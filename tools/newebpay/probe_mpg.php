<?php
/**
 * Synthetic MPG probe - is this method actually enabled at NewebPay for this shop?
 *
 * Builds one canonical MPG request with a throwaway order number and posts it to the gateway.
 * No shop, no database, no order. PASS = NewebPay answered with its payment page echoing the
 * order number; FAIL = a refusal code (MPG02003 = product not enabled at NewebPay's side, etc).
 *
 * Reads, from the environment or a .env file in the current directory:
 *   NEWEBPAY_MERCHANT_ID  NEWEBPAY_HASH_KEY (32 chars)  NEWEBPAY_HASH_IV (16 chars)
 *   NEWEBPAY_ENV          sandbox | production          (default sandbox)
 *   NEWEBPAY_CALLBACK_BASE https://... (public https base for NotifyURL/ReturnURL; a tunnel is fine)
 *   NEWEBPAY_VERSION      MPG `Version` field (default 2.3 - confirm against the NDNF manual you read)
 *
 * Usage:
 *   php tools/newebpay/probe_mpg.php                 # probe CREDIT
 *   php tools/newebpay/probe_mpg.php WEBATM          # probe one method flag (CREDIT, WEBATM, VACC, CVS,
 *                                                    #   BARCODE, LINEPAY, APPLEPAY, ANDROIDPAY, ...)
 *   php tools/newebpay/probe_mpg.php --dry-run       # build and print field names/lengths, do not post
 *   php tools/newebpay/probe_mpg.php --selftest      # no credentials: round-trip the codec and signer
 *
 * Exit codes: 0 PASS, 2 FAIL (refusal code named), 3 UNKNOWN, 1 configuration error.
 * Never prints MerchantID, HashKey, HashIV, TradeInfo or TradeSha values - lengths only.
 *
 * Adapted from a shipped integration's tools/ops/probe-newebpay-mpg-synthetic.php (2026-08-17).
 * The protocol facts (AES-256-CBC hex over the URL-encoded fields, TradeSha = SHA-256 upper of
 * "HashKey={key}&{TradeInfo}&HashIV={iv}") are NDNF-1.2.x; re-read the manual if it moves.
 */
declare(strict_types=1);

const STAGE = 'https://ccore.newebpay.com/MPG/mpg_gateway';
const PROD = 'https://core.newebpay.com/MPG/mpg_gateway';
const METHODS = ['CREDIT', 'WEBATM', 'VACC', 'CVS', 'BARCODE', 'LINEPAY', 'APPLEPAY', 'ANDROIDPAY', 'SAMSUNGPAY', 'ESUNWALLET', 'TAIWANPAY', 'UNIONPAY', 'BITOPAY', 'AFTEE', 'OPPAY'];
const REFUSALS = ['MPG02003', 'MPG00040', 'MPG01001', 'MPG01002', 'CHK00007', 'CHK00001', 'TRA10014', 'TRA10015', 'TRA10021'];

function env(string $k, string $default = ''): string
{
    $v = getenv($k);
    return $v === false ? $default : trim($v);
}

function loadDotEnv(string $path): void
{
    if (!is_file($path)) {
        return;
    }
    foreach (file($path, FILE_IGNORE_NEW_LINES | FILE_SKIP_EMPTY_LINES) as $line) {
        if ($line[0] === '#' || !str_contains($line, '=')) {
            continue;
        }
        [$k, $v] = explode('=', $line, 2);
        $k = trim($k);
        $v = trim(trim($v), "\"'");
        if ($k !== '' && getenv($k) === false) {
            putenv("{$k}={$v}");
        }
    }
}

function encrypt(string $plain, string $key, string $iv): string
{
    $c = openssl_encrypt($plain, 'AES-256-CBC', $key, OPENSSL_RAW_DATA, $iv);
    if ($c === false) {
        throw new RuntimeException('openssl_encrypt failed');
    }
    return bin2hex($c);
}

function decrypt(string $hex, string $key, string $iv): string
{
    $raw = hex2bin($hex);
    if ($raw === false) {
        throw new RuntimeException('not hex');
    }
    $p = openssl_decrypt($raw, 'AES-256-CBC', $key, OPENSSL_RAW_DATA | OPENSSL_ZERO_PADDING, $iv);
    if ($p === false) {
        throw new RuntimeException('openssl_decrypt failed');
    }
    $pad = ord($p[strlen($p) - 1]);
    return substr($p, 0, -$pad);
}

function tradeSha(string $tradeInfo, string $key, string $iv): string
{
    return strtoupper(hash('sha256', 'HashKey=' . $key . '&' . $tradeInfo . '&HashIV=' . $iv));
}

$args = array_slice($argv, 1);
if (in_array('--selftest', $args, true)) {
    $key = str_repeat('k', 32);
    $iv = str_repeat('i', 16);
    $plain = http_build_query(['MerchantID' => 'MS000', 'Amt' => 100, 'ItemDesc' => '測試 & test']);
    $cipher = encrypt($plain, $key, $iv);
    $ok = ctype_xdigit($cipher) && decrypt($cipher, $key, $iv) === $plain;
    $sha = tradeSha($cipher, $key, $iv);
    $ok = $ok && strlen($sha) === 64 && ctype_xdigit($sha) && $sha === strtoupper($sha);
    // signing the plaintext must NOT equal signing the ciphertext (the classic mistake)
    $ok = $ok && tradeSha($plain, $key, $iv) !== $sha;
    echo $ok ? "SELFTEST PASS — AES-256-CBC hex round-trip, TradeSha 64 upper hex over ciphertext\n" : "SELFTEST FAIL\n";
    exit($ok ? 0 : 1);
}

loadDotEnv(getcwd() . '/.env');
$mid = env('NEWEBPAY_MERCHANT_ID');
$key = env('NEWEBPAY_HASH_KEY');
$iv = env('NEWEBPAY_HASH_IV');
$mode = env('NEWEBPAY_ENV', 'sandbox');
$base = rtrim(env('NEWEBPAY_CALLBACK_BASE'), '/');
$version = env('NEWEBPAY_VERSION', '2.3');
$method = 'CREDIT';
foreach ($args as $a) {
    if (in_array(strtoupper($a), METHODS, true)) {
        $method = strtoupper($a);
    }
}
$dry = in_array('--dry-run', $args, true);

$problems = [];
if ($mid === '') { $problems[] = 'NEWEBPAY_MERCHANT_ID missing'; }
if (strlen($key) !== 32) { $problems[] = 'NEWEBPAY_HASH_KEY must be 32 chars (got ' . strlen($key) . ')'; }
if (strlen($iv) !== 16) { $problems[] = 'NEWEBPAY_HASH_IV must be 16 chars (got ' . strlen($iv) . ')'; }
if (!str_starts_with($base, 'https://')) { $problems[] = 'NEWEBPAY_CALLBACK_BASE must be a public https URL (use a tunnel on localhost)'; }
if (!in_array($mode, ['sandbox', 'production'], true)) { $problems[] = 'NEWEBPAY_ENV must be sandbox or production'; }
if ($problems) {
    fwrite(STDERR, "CONFIG: " . implode('; ', $problems) . "\n");
    exit(1);
}
if ($mode === 'production' && !in_array('--i-mean-production', $args, true)) {
    fwrite(STDERR, "REFUSED: NEWEBPAY_ENV=production. A probe against core.newebpay.com creates a real (unpaid) transaction. Re-run with --i-mean-production if that is intended.\n");
    exit(1);
}

$orderNo = 'PROBE_' . date('YmdHis');
$fields = [
    'MerchantID' => $mid,
    'RespondType' => 'JSON',
    'TimeStamp' => (string) time(),
    'Version' => $version,
    'MerchantOrderNo' => $orderNo,
    'Amt' => 1,
    'ItemDesc' => 'MPG synthetic probe',
    'NotifyURL' => $base . '/callback/newebpay/payment',
    'ReturnURL' => $base . '/order/probe',
    'LangType' => 'zh-tw',
];
foreach (METHODS as $m) {
    $fields[$m] = $m === $method ? '1' : '0';
}
$tradeInfo = encrypt(http_build_query($fields), $key, $iv);
$post = ['MerchantID' => $mid, 'TradeInfo' => $tradeInfo, 'TradeSha' => tradeSha($tradeInfo, $key, $iv), 'Version' => $version];
$url = $mode === 'production' ? PROD : STAGE;

printf("POST %s  (env=%s, method=%s, order=%s)\n", $url, $mode, $method, $orderNo);
foreach ($post as $k => $v) {
    printf("  %-12s %s\n", $k, in_array($k, ['MerchantID', 'TradeInfo', 'TradeSha'], true) ? '<redacted, ' . strlen($v) . ' chars>' : $v);
}
if ($dry) {
    echo "DRY RUN — not posted.\n";
    exit(0);
}

$ch = curl_init($url);
curl_setopt_array($ch, [
    CURLOPT_POST => true,
    CURLOPT_POSTFIELDS => http_build_query($post),
    CURLOPT_RETURNTRANSFER => true,
    CURLOPT_FOLLOWLOCATION => false,
    CURLOPT_HTTPHEADER => ['User-Agent: Mozilla/5.0 (ecommerce-cia mpg-probe)', 'Accept: text/html'],
    CURLOPT_TIMEOUT => 30,
]);
$body = curl_exec($ch);
$status = curl_getinfo($ch, CURLINFO_HTTP_CODE);
$err = curl_error($ch);
curl_close($ch);
if ($body === false) {
    fwrite(STDERR, "curl error: {$err}\n");
    exit(3);
}
printf("HTTP %d, %d bytes\n", $status, strlen((string) $body));
foreach (REFUSALS as $code) {
    if (str_contains((string) $body, $code)) {
        printf("FAIL — %s in response. %s\n", $code, $code === 'MPG02003' ? 'Product not enabled at NewebPay for this shop: check the console toggle, then this is a vendor-side enablement (dated wait), not a code problem.' : 'Look the code up in the NDNF error table you downloaded.');
        exit(2);
    }
}
if (stripos((string) $body, '藍新金流') !== false && str_contains((string) $body, $orderNo)) {
    echo "PASS — NewebPay returned its payment page echoing the order number; {$method} is enabled for this shop in {$mode}.\n";
    exit(0);
}
echo "UNKNOWN — neither a known refusal code nor the payment page shape. Open the same request in a browser and read the page.\n";
exit(3);
