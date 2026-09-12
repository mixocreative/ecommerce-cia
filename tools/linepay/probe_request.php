<?php
/**
 * Synthetic LINE Pay Online API probe - do these credentials work on this environment, and is the shop
 * allowed to request a payment?
 *
 * Posts one 1 TWD payment request (POST /v3/payments/request, or /v4 with --v4) with a throwaway orderId.
 * Nothing is charged: a request only reserves a transaction and returns a payment URL the customer would
 * have to open and approve. PASS = returnCode 0000 with info.paymentUrl.web + info.transactionId.
 * FAIL = a named returnCode:
 *   1104 merchant not registered  -> Channel ID wrong, or sandbox credentials against api-pay.line.me (or vice versa)
 *   1106 request header error     -> Channel Secret wrong, or the MAC was computed over different bytes than sent
 *   1178 currency not supported   -> the merchant's contract currency is not TWD (or the field is wrong)
 *   1183 / 1184 amount limits     -> 1 TWD is below the shop's minimum; retry with --amount N
 *   1105 unavailable              -> merchant suspended / not yet approved: a vendor-side wait, not code
 *   2101 / 2102 parameter / JSON  -> request shape; run --dry-run and compare with the reference page
 *
 * Env or ./.env: LINEPAY_CHANNEL_ID, LINEPAY_CHANNEL_SECRET, LINEPAY_ENV sandbox|production (default sandbox),
 *                LINEPAY_CALLBACK_BASE https://... (confirmUrl / cancelUrl base; a tunnel is fine)
 * Usage:
 *   php tools/linepay/probe_request.php              # post to the sandbox
 *   php tools/linepay/probe_request.php --dry-run    # build, print shape with the secret redacted, do not post
 *   php tools/linepay/probe_request.php --v4         # same against /v4 (adds info.paymentProvider on confirm)
 *   php tools/linepay/probe_request.php --amount 100
 *   php tools/linepay/probe_request.php --check <transactionId>   # GET /v3/payments/requests/{id}/check
 *   php tools/linepay/probe_request.php --confirm <transactionId> [--amount N]   # POST .../confirm after the customer approved (0110)
 *   php tools/linepay/probe_request.php --refund <transactionId> [--amount N]    # POST .../refund (omit --amount for full)
 *   php tools/linepay/probe_request.php --details <transactionId>  # GET /v3/payments?transactionId=
 * Exit 0 PASS, 2 FAIL (code named), 3 UNKNOWN, 1 configuration error. Prints the Channel ID length only, never
 * the secret, never the signature.
 * Reference: https://developers-pay.line.me/online-api-v3/request-payment (read 2026-09-13).
 */
declare(strict_types=1);

require __DIR__ . '/sign.php';

const HOSTS = ['sandbox' => 'https://sandbox-api-pay.line.me', 'production' => 'https://api-pay.line.me'];
const WHY = [
    '1104' => 'The merchant is not registered on the merchant center - Channel ID wrong for this environment (sandbox credentials against api-pay.line.me, or the reverse). Re-copy from Merchant Center > 開發者工具 > 管理連結金鑰.',
    '1105' => 'LINE Pay is currently unavailable for this merchant - the account is suspended or not yet approved. Vendor-side: put a dated wait on the readiness card.',
    '1106' => 'Request header error - the HMAC did not verify. Channel Secret wrong, or the MAC was computed over a different body string than the one sent (key order, whitespace). Run sign.php selftest, then sign the exact bytes you post.',
    '1124' => 'Amount error - amount must equal the sum of packages[].amount (+ userFee); TWD takes integers only.',
    '1172' => 'An order with this orderId already exists - orderId must be unique per request; this probe uses a timestamped one, so the clock or a retry loop is reusing ids.',
    '1178' => 'Currency not supported for this merchant - the contract currency is not TWD, or the field is misspelt.',
    '1183' => 'Amount below the minimum set for this shop - retry with --amount N.',
    '1184' => 'Amount above the maximum set for this shop.',
    '1198' => 'Duplicate API request - the same request is already being processed (a retry fired inside the read timeout). Set the read timeout to at least 10 s and do not retry blindly.',
    '2101' => 'Parameter error - a required field is missing or malformed. Compare --dry-run output with the reference page.',
    '2102' => 'JSON data format error - the body is not valid JSON (or Content-Type is not application/json).',
    '9000' => 'Internal error at LINE Pay - retry later; if it persists, it is theirs, not yours.',
];

$args = array_slice($argv, 1);
loadDotEnv(getcwd() . '/.env');
$cid = env('LINEPAY_CHANNEL_ID'); $sec = env('LINEPAY_CHANNEL_SECRET'); $mode = env('LINEPAY_ENV', 'sandbox');
$base = rtrim(env('LINEPAY_CALLBACK_BASE'), '/');
$dry = in_array('--dry-run', $args, true);
$ver = in_array('--v4', $args, true) ? 'v4' : 'v3';
$amount = 1; $check = null; $confirm = null; $refund = null; $details = null; $amountGiven = false;
for ($i = 0; $i < count($args); $i++) {
    if ($args[$i] === '--amount' && isset($args[$i + 1])) { $amount = (int) $args[$i + 1]; $amountGiven = true; }
    if ($args[$i] === '--check' && isset($args[$i + 1])) { $check = $args[$i + 1]; }
    if ($args[$i] === '--confirm' && isset($args[$i + 1])) { $confirm = $args[$i + 1]; }
    if ($args[$i] === '--refund' && isset($args[$i + 1])) { $refund = $args[$i + 1]; }
    if ($args[$i] === '--details' && isset($args[$i + 1])) { $details = $args[$i + 1]; }
}

$problems = [];
if ($cid === '') { $problems[] = 'LINEPAY_CHANNEL_ID missing'; }
if ($sec === '') { $problems[] = 'LINEPAY_CHANNEL_SECRET missing'; }
if (!str_starts_with($base, 'https://')) { $problems[] = 'LINEPAY_CALLBACK_BASE must be a public https URL (confirmUrl/cancelUrl must be TLS 1.2+; use a tunnel on localhost)'; }
if (!isset(HOSTS[$mode])) { $problems[] = 'LINEPAY_ENV must be sandbox or production'; }
if ($amount < 1) { $problems[] = '--amount must be a positive integer (TWD has no decimals)'; }
if ($problems) { fwrite(STDERR, 'CONFIG: ' . implode('; ', $problems) . "\n"); exit(1); }
if ($mode === 'production' && !in_array('--i-mean-production', $args, true)) {
    fwrite(STDERR, "REFUSED: LINEPAY_ENV=production. A request against api-pay.line.me creates a real reservation visible in the merchant center. Re-run with --i-mean-production if that is intended.\n");
    exit(1);
}

function call(string $method, string $path, string $payload, string $cid, string $sec, string $mode): array
{
    $url = HOSTS[$mode] . $path . ($method === 'GET' && $payload !== '' ? '?' . $payload : '');
    $h = [];
    foreach (linepayHeaders($cid, $sec, $method, $path, $payload) as $k => $v) { $h[] = "{$k}: {$v}"; }
    $ch = curl_init($url);
    curl_setopt_array($ch, [
        CURLOPT_CUSTOMREQUEST => $method,
        CURLOPT_POSTFIELDS => $method === 'POST' ? $payload : null,
        CURLOPT_RETURNTRANSFER => true,
        CURLOPT_HTTPHEADER => array_merge($h, ['User-Agent: Mozilla/5.0 (ecommerce-cia linepay-probe)']),
        CURLOPT_TIMEOUT => 40, // the reference asks for >=10 s (request) / >=40 s (confirm) read timeouts
    ]);
    $body = curl_exec($ch);
    $status = curl_getinfo($ch, CURLINFO_HTTP_CODE);
    $err = curl_error($ch);
    curl_close($ch);
    if ($body === false) { fwrite(STDERR, "curl error: {$err}\n"); exit(3); }
    // transactionId is a 19-digit integer; quote it before json_decode so PHP does not round it to a float
    $body = preg_replace('/:\s*(\d{16,})\b/', ': "$1"', (string) $body) ?? (string) $body;
    return [$status, json_decode($body, true), $body];
}

if ($check !== null) {
    $path = "/{$ver}/payments/requests/{$check}/check";
    printf("GET %s%s  (env=%s, channel id %d chars)\n", HOSTS[$mode], $path, $mode, strlen($cid));
    if ($dry) { echo "DRY RUN — not sent.\n"; exit(0); }
    [$status, $j, $raw] = call('GET', $path, '', $cid, $sec, $mode);
    $code = (string) ($j['returnCode'] ?? '');
    $meaning = ['0000' => 'customer has not completed LINE Pay authentication yet', '0110' => 'authenticated - you may call confirm now', '0121' => 'customer cancelled or the authentication window expired', '0122' => 'payment failed', '0123' => 'payment completed'][$code] ?? (WHY[$code] ?? 'see the result-code table');
    printf("HTTP %d returnCode=%s — %s\n", $status, $code === '' ? '(none)' : $code, $meaning);
    exit(in_array($code, ['0000', '0110', '0123'], true) ? 0 : ($code === '' ? 3 : 2));
}

if ($confirm !== null || $refund !== null || $details !== null) {
    // confirm: the amount and currency MUST equal the request's; the probe requested --amount (default 1) TWD.
    // refund: refundAmount omitted = full refund. details: GET with the query string signed.
    if ($confirm !== null) { $method = 'POST'; $path = "/{$ver}/payments/{$confirm}/confirm"; $payload = json_encode(['amount' => $amount, 'currency' => 'TWD']); }
    elseif ($refund !== null) { $method = 'POST'; $path = "/{$ver}/payments/{$refund}/refund"; $payload = $amountGiven ? json_encode(['refundAmount' => $amount]) : '{}'; }
    else { $method = 'GET'; $path = "/{$ver}/payments"; $payload = 'transactionId=' . $details; }
    printf("%s %s%s  (env=%s, body/query %s)
", $method, HOSTS[$mode], $path, $mode, $payload);
    if ($dry) { echo "DRY RUN — not sent.
"; exit(0); }
    [$status, $j, $raw] = call($method, $path, (string) $payload, $cid, $sec, $mode);
    $code = (string) ($j['returnCode'] ?? $j['resultCode'] ?? '');
    $msg = (string) ($j['returnMessage'] ?? $j['statusMessage'] ?? '');
    printf("HTTP %d returnCode=%s (%s)
", $status, $code === '' ? '(none)' : $code, $msg);
    if ($code === '0000') {
        echo json_encode($j['info'] ?? [], JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES | JSON_PRETTY_PRINT), "
";
        if ($confirm !== null) { echo "PASS — payment confirmed; payInfo above is the money proof (BALANCE / CREDIT_CARD / POINT).
"; }
        if ($refund !== null) { echo "PASS — refunded; refundTransactionId above.
"; }
        exit(0);
    }
    $extra = ['1169' => 'customer has not authenticated on the LINE Pay page yet (live: confirm before approval returns this) - poll --check for 0110 first', '1150' => 'no confirmed transaction with this id (live: --details on an unconfirmed reservation returns this; details lists confirmed payments only)', '1145' => 'confirm already in progress - do not retry; poll --check', '1152' => 'already confirmed - treat as done, read --details', '1172' => 'already confirmed - the sandbox answers a second confirm with 1172 (live 2026-09-13); treat as done, read --details', '1165' => 'already refunded - treat as done', '1159' => 'no payment request for this id, or it expired - the customer never approved, or you confirmed a different id'];
    printf("FAIL — returnCode %s. %s
", $code, $extra[$code] ?? (WHY[$code] ?? 'see the result-code table'));
    exit($code === '' ? 3 : 2);
}

$orderId = 'PROBE_' . date('YmdHis') . '_' . substr(bin2hex(random_bytes(3)), 0, 6);
$req = [
    'amount' => $amount,
    'currency' => 'TWD',
    'orderId' => $orderId,
    'packages' => [[
        'id' => 'probe',
        'amount' => $amount,
        'name' => 'ecommerce-cia probe',
        'products' => [['id' => 'probe-1', 'name' => 'LINE Pay synthetic probe', 'quantity' => 1, 'price' => $amount]],
    ]],
    'redirectUrls' => ['confirmUrl' => $base . '/order/linepay/confirm', 'cancelUrl' => $base . '/order/linepay/cancel'],
];
$payload = json_encode($req, JSON_UNESCAPED_SLASHES | JSON_UNESCAPED_UNICODE);
$path = "/{$ver}/payments/request";
printf("POST %s%s  (env=%s, api=%s, orderId=%s, amount=%d TWD, channel id %d chars, secret %d chars)\n", HOSTS[$mode], $path, $mode, $ver, $orderId, $amount, strlen($cid), strlen($sec));
echo "  body " . strlen((string) $payload) . " bytes: " . $payload . "\n";
echo "  headers X-LINE-ChannelId <redacted>, X-LINE-Authorization-Nonce <uuid4>, X-LINE-Authorization <redacted, base64 of 32 bytes>\n";
if ($dry) { echo "DRY RUN — not posted.\n"; exit(0); }

[$status, $j, $raw] = call('POST', $path, (string) $payload, $cid, $sec, $mode);
printf("HTTP %d, %d bytes\n", $status, strlen($raw));
if (!is_array($j)) { echo "UNKNOWN — response is not JSON: " . substr($raw, 0, 200) . "\n"; exit(3); }
$code = (string) ($j['returnCode'] ?? $j['resultCode'] ?? '');
$msg = (string) ($j['returnMessage'] ?? $j['statusMessage'] ?? '');
if ($code === '0000' && isset($j['info']['paymentUrl']['web'], $j['info']['transactionId'])) {
    printf("PASS — returnCode 0000; transactionId %s; payment page %s\n", $j['info']['transactionId'], $j['info']['paymentUrl']['web']);
    echo "  Open that URL on a PC and ALLOW POP-UPS: the simulator opens as a 320x560 pop-up with a PAY NOW button (no LINE login). Then poll --check <transactionId> until 0110, then --confirm <transactionId>. Never confirm before 0110 - it kills the reservation (1169, then 0122).\n";
    echo "  In the sandbox only paymentUrl.web works; paymentUrl.app is production-only.\n";
    exit(0);
}
if ($code !== '') {
    printf("FAIL — returnCode %s (%s). %s\n", $code, $msg, WHY[$code] ?? 'Look the code up in the result-code table of the Online API reference.');
    exit(2);
}
echo "UNKNOWN — no returnCode in the response: " . substr($raw, 0, 300) . "\n";
exit(3);
