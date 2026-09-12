<?php
/**
 * NewebPay callback verifier and simulator.
 *
 * verify : take a raw NotifyURL/ReturnURL/CustomerURL POST body, check TradeSha over TradeInfo
 *          BEFORE decrypting, decrypt, print the decoded payload as JSON. Use it to look at what
 *          the sandbox actually sent, and to prove your endpoint's verification matches this one.
 * make   : build a signed callback body from a JSON payload, so a NotifyURL handler can be
 *          exercised locally (curl -d @body.txt https://localhost/callback) without waiting for
 *          the sandbox. The body is exactly what NewebPay would post for that payload.
 *
 * Usage:
 *   php tools/newebpay/callback.php verify < body.txt
 *   php tools/newebpay/callback.php make   < payload.json  > body.txt
 *   php tools/newebpay/callback.php selftest
 *
 * Keys from the environment or ./.env: NEWEBPAY_HASH_KEY (32), NEWEBPAY_HASH_IV (16).
 * Payload shape for make (NDNF-1.2.x "Result" object; check the manual's field table):
 *   {"Status":"SUCCESS","Message":"授權成功","Result":{"MerchantID":"MS...","Amt":100,
 *    "TradeNo":"26091212345678","MerchantOrderNo":"ORDER_1","PaymentType":"CREDIT",
 *    "RespondType":"JSON","PayTime":"2026-09-12 12:00:00","IP":"1.2.3.4","EscrowBank":"HNCB"}}
 * Exit codes: 0 ok, 2 signature mismatch, 1 usage/config error.
 */
declare(strict_types=1);

function env(string $k, string $d = ''): string { $v = getenv($k); return $v === false ? $d : trim($v); }
function loadDotEnv(string $p): void
{
    if (!is_file($p)) { return; }
    foreach (file($p, FILE_IGNORE_NEW_LINES | FILE_SKIP_EMPTY_LINES) as $l) {
        if ($l[0] === '#' || !str_contains($l, '=')) { continue; }
        [$k, $v] = explode('=', $l, 2);
        $k = trim($k); $v = trim(trim($v), "\"'");
        if ($k !== '' && getenv($k) === false) { putenv("{$k}={$v}"); }
    }
}
function encrypt(string $plain, string $key, string $iv): string
{
    $c = openssl_encrypt($plain, 'AES-256-CBC', $key, OPENSSL_RAW_DATA, $iv);
    if ($c === false) { throw new RuntimeException('encrypt failed'); }
    return bin2hex($c);
}
function decrypt(string $hex, string $key, string $iv): string
{
    $raw = hex2bin($hex);
    if ($raw === false) { throw new RuntimeException('TradeInfo is not hex'); }
    $p = openssl_decrypt($raw, 'AES-256-CBC', $key, OPENSSL_RAW_DATA | OPENSSL_ZERO_PADDING, $iv);
    if ($p === false) { throw new RuntimeException('decrypt failed (wrong key/iv or corrupt body)'); }
    $pad = ord($p[strlen($p) - 1]);
    if ($pad < 1 || $pad > 16) { throw new RuntimeException('bad PKCS7 padding (wrong key/iv?)'); }
    return substr($p, 0, -$pad);
}
function tradeSha(string $ti, string $key, string $iv): string
{
    return strtoupper(hash('sha256', 'HashKey=' . $key . '&' . $ti . '&HashIV=' . $iv));
}

$cmd = $argv[1] ?? '';
if ($cmd === 'selftest') {
    $key = str_repeat('a', 32); $iv = str_repeat('b', 16);
    $payload = json_encode(['Status' => 'SUCCESS', 'Result' => ['MerchantOrderNo' => 'X1', 'Amt' => 5]], JSON_UNESCAPED_UNICODE);
    $ti = encrypt($payload, $key, $iv);
    $body = http_build_query(['Status' => 'SUCCESS', 'MerchantID' => 'MS1', 'Version' => '2.3', 'TradeInfo' => $ti, 'TradeSha' => tradeSha($ti, $key, $iv)]);
    parse_str($body, $f);
    $ok = hash_equals(tradeSha($f['TradeInfo'], $key, $iv), $f['TradeSha']) && decrypt($f['TradeInfo'], $key, $iv) === $payload;
    // a tampered TradeInfo must fail the signature
    $t = $f; $t['TradeInfo'] = substr($t['TradeInfo'], 0, -2) . '00';
    $ok = $ok && !hash_equals(tradeSha($t['TradeInfo'], $key, $iv), $t['TradeSha']);
    if (!$ok) { echo "SELFTEST FAIL — synthetic round-trip\n"; exit(1); }
    // Vendor known-answer: the NDNF-1.2.5 manual (§4.1.4 Step 5) prints a complete NotifyURL body signed
    // with its example keys. verify must accept it, and the decoded RespondType=String payload must say
    // PaymentType=CREDIT — the same path a real sandbox post takes.
    $kat = json_decode((string) file_get_contents(__DIR__ . '/manual-example.json'), true);
    if (!is_array($kat)) { echo "SELFTEST FAIL — manual-example.json missing\n"; exit(1); }
    parse_str($kat['callback_body'], $kf);
    $katOk = hash_equals(tradeSha((string) $kf['TradeInfo'], $kat['hash_key'], $kat['hash_iv']), (string) $kf['TradeSha']);
    $plain = $katOk ? decrypt((string) $kf['TradeInfo'], $kat['hash_key'], $kat['hash_iv']) : '';
    parse_str($plain, $kp);
    foreach ($kat['callback_expect'] as $k => $v) { $katOk = $katOk && (string) ($kp[$k] ?? '') === (string) $v; }
    // and the request-side example too, so make/verify share one proven codec
    $katOk = $katOk && hash_equals($kat['trade_info'], encrypt($kat['plain'], $kat['hash_key'], $kat['hash_iv']));
    echo $katOk ? "SELFTEST PASS — synthetic round-trip + tamper refused; vendor known-answer NDNF-1.2.5 §4.1 callback verified and decoded (PaymentType=CREDIT)\n" : "SELFTEST FAIL — vendor known-answer not reproduced\n";
    exit($katOk ? 0 : 1);
}

loadDotEnv(getcwd() . '/.env');
$key = env('NEWEBPAY_HASH_KEY'); $iv = env('NEWEBPAY_HASH_IV');
if (strlen($key) !== 32 || strlen($iv) !== 16) {
    fwrite(STDERR, "CONFIG: NEWEBPAY_HASH_KEY must be 32 chars and NEWEBPAY_HASH_IV 16 (got " . strlen($key) . '/' . strlen($iv) . ")\n");
    exit(1);
}
$in = stream_get_contents(STDIN) ?: '';

if ($cmd === 'verify') {
    parse_str(trim($in), $f);
    if (!isset($f['TradeInfo'], $f['TradeSha'])) {
        fwrite(STDERR, "body has no TradeInfo/TradeSha — this is not an MPG callback (logistics pushes use EncryptData_/HashData_)\n");
        exit(1);
    }
    if (!hash_equals(tradeSha((string) $f['TradeInfo'], $key, $iv), strtoupper(trim((string) $f['TradeSha'])))) {
        fwrite(STDERR, "SIGNATURE MISMATCH — refuse this body. (Wrong HashKey/HashIV for this MerchantID, or a tampered/forged post.)\n");
        exit(2);
    }
    $plain = decrypt((string) $f['TradeInfo'], $key, $iv);
    $decoded = json_decode($plain, true);
    if ($decoded === null) { parse_str($plain, $decoded); }
    echo json_encode(['verified' => true, 'outer' => array_diff_key($f, ['TradeInfo' => 1, 'TradeSha' => 1]), 'payload' => $decoded], JSON_UNESCAPED_UNICODE | JSON_PRETTY_PRINT), "\n";
    exit(0);
}

if ($cmd === 'make') {
    $payload = json_decode(trim($in), true);
    if (!is_array($payload)) { fwrite(STDERR, "stdin must be a JSON object payload\n"); exit(1); }
    $ti = encrypt(json_encode($payload, JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES), $key, $iv);
    echo http_build_query([
        'Status' => $payload['Status'] ?? 'SUCCESS',
        'MerchantID' => $payload['Result']['MerchantID'] ?? env('NEWEBPAY_MERCHANT_ID', 'MS0'),
        'Version' => env('NEWEBPAY_VERSION', '2.3'),
        'TradeInfo' => $ti,
        'TradeSha' => tradeSha($ti, $key, $iv),
    ]), "\n";
    exit(0);
}

fwrite(STDERR, "usage: callback.php verify|make|selftest\n");
exit(1);
