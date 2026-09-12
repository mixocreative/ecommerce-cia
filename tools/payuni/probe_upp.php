<?php
/**
 * Synthetic UPP probe - is this method enabled on this PAYUNi shop?
 *
 * Posts one 整合式支付頁 (UPP Ver 2.0) request with a throwaway MerTradeNo (docs #/7/34).
 *   PASS     PAYUNi answered with its payment page
 *   FAIL     a JSON/form reply whose Status is not SUCCESS: DEF01007 = HashInfo mismatch (keys),
 *            DEF01005 = shop not found on this environment, DEF01002 = decrypt failed, API00010/11 = envelope shape
 *   UNKNOWN  neither
 * Env or ./.env: PAYUNI_MER_ID, PAYUNI_AES_KEY (32), PAYUNI_AES_IV (16), PAYUNI_ENV sandbox|production,
 *                PAYUNI_CALLBACK_BASE https://... (NotifyURL must be on port 80 or 443)
 * Usage: php tools/payuni/probe_upp.php [Credit|ATM|CVS|LinePay|ICash|Aftee|JKoPay|ApplePay|GooglePay|SamsungPay] [--dry-run] [--i-mean-production]
 * Never prints keys, EncryptInfo or HashInfo values - lengths only. Not yet verified live (no sandbox shop on hand).
 */
declare(strict_types=1);

require_once __DIR__ . '/lib.php';

const SANDBOX = 'https://sandbox-api.payuni.com.tw/api/upp';
const PROD = 'https://api.payuni.com.tw/api/upp';
const FLAGS = ['Credit', 'ATM', 'CVS', 'LinePay', 'ICash', 'Aftee', 'JKoPay', 'ApplePay', 'GooglePay', 'SamsungPay', 'CreditUnionPay'];

$args = array_slice($argv, 1);
loadDotEnv(getcwd() . '/.env');
$mid = env('PAYUNI_MER_ID'); $key = env('PAYUNI_AES_KEY'); $iv = env('PAYUNI_AES_IV');
$mode = env('PAYUNI_ENV', 'sandbox'); $base = rtrim(env('PAYUNI_CALLBACK_BASE'), '/');
$flag = 'Credit';
foreach ($args as $a) { foreach (FLAGS as $f) { if (strcasecmp($a, $f) === 0) { $flag = $f; } } }
$dry = in_array('--dry-run', $args, true);

$problems = [];
if ($mid === '') { $problems[] = 'PAYUNI_MER_ID missing'; }
if (strlen($key) !== 32) { $problems[] = 'PAYUNI_AES_KEY must be 32 chars (got ' . strlen($key) . ')'; }
if (strlen($iv) !== 16) { $problems[] = 'PAYUNI_AES_IV must be 16 chars (got ' . strlen($iv) . ')'; }
if (!str_starts_with($base, 'https://')) { $problems[] = 'PAYUNI_CALLBACK_BASE must be https (NotifyURL: port 80/443 only)'; }
if (preg_match('#^https://[^/]+:(\d+)#', $base, $pm) === 1 && !in_array($pm[1], ['80', '443'], true)) { $problems[] = 'NotifyURL port must be 80 or 443 (docs #/7/34)'; }
if (!in_array($mode, ['sandbox', 'production'], true)) { $problems[] = 'PAYUNI_ENV must be sandbox or production'; }
if ($problems) { fwrite(STDERR, 'CONFIG: ' . implode('; ', $problems) . "\n"); exit(1); }
if ($mode === 'production' && !in_array('--i-mean-production', $args, true)) {
    fwrite(STDERR, "REFUSED: PAYUNI_ENV=production creates a real order. Re-run with --i-mean-production if intended.\n");
    exit(1);
}

$tradeNo = 'PROBE' . date('YmdHis') . substr((string) mt_rand(1000, 9999), 0, 4);   // <=25, [A-Za-z0-9_-], unique per 10 min
$fields = [
    'MerID' => $mid,
    'MerTradeNo' => $tradeNo,
    'TradeAmt' => '30',   // >= every method's floor except ATM (15) and CVS (30)
    'Timestamp' => (string) time(),
    'ReturnURL' => $base . '/payuni/return',
    'NotifyURL' => $base . '/payuni/notify',
    'ProdDesc' => 'UPP synthetic probe',
    'TradeLExpireSec' => '60',
    $flag => '1',
];
$enc = payuniEncrypt($fields, $key, $iv);
$post = ['MerID' => $mid, 'Version' => '2.0', 'EncryptInfo' => $enc, 'HashInfo' => payuniHash($enc, $key, $iv)];
$url = $mode === 'production' ? PROD : SANDBOX;

printf("POST %s  (env=%s, flag=%s, MerTradeNo=%s)\n", $url, $mode, $flag, $tradeNo);
foreach ($post as $k => $v) { printf("  %-12s %s\n", $k, $k === 'Version' ? $v : '<redacted, ' . strlen($v) . ' chars>'); }
if ($dry) { echo "DRY RUN — not posted.\n"; exit(0); }

$ch = curl_init($url);
curl_setopt_array($ch, [CURLOPT_POST => true, CURLOPT_POSTFIELDS => http_build_query($post), CURLOPT_RETURNTRANSFER => true, CURLOPT_FOLLOWLOCATION => false, CURLOPT_TIMEOUT => 30,
    CURLOPT_HTTPHEADER => ['User-Agent: Mozilla/5.0 (ecommerce-cia upp-probe)']]);
$body = (string) curl_exec($ch); $status = curl_getinfo($ch, CURLINFO_HTTP_CODE); $err = curl_error($ch); curl_close($ch);
if ($body === '' && $err !== '') { fwrite(STDERR, "curl error: {$err}\n"); exit(3); }
printf("HTTP %d, %d bytes\n", $status, strlen($body));
if (($dump = getenv('PAYUNI_PROBE_DUMP')) !== false && $dump !== '') { file_put_contents($dump, $body); }
// Verified live 2026-09-13: the payment page embeds `window.JS_INFO = {"success": bool, "message": "...", "data": [...]}`.
// Fake credentials -> success:false, message 商店不存在. That object is the verdict; the brand name is on every page.
$why = ['DEF01007' => 'HashInfo mismatch: AES key/IV do not match this MerID on this environment.', 'DEF01005' => 'shop not found on this environment (sandbox vs production MerID).', 'DEF01002' => 'decrypt failed: wrong key/IV or envelope shape.', 'API00010' => 'EncryptInfo format error.', 'API00011' => 'HashInfo format error.'];
if (preg_match('/window\.JS_INFO\s*=\s*(\{.*?\});/s', $body, $jm) === 1 && ($info = json_decode($jm[1], true)) !== null) {
    $msg = (string) ($info['message'] ?? '');
    if (($info['success'] ?? false) === true) {
        echo "PASS — PAYUNi served its payment page (JS_INFO.success=true); {$flag} accepted for this shop in {$mode}. Which methods are shown is the console's decision — open the page to confirm.\n";
        exit(0);
    }
    $hint = match (true) {
        str_contains($msg, '商店不存在') => 'MerID is not a shop on this environment (sandbox vs production), or the shop was never created.',
        str_contains($msg, '解密') || str_contains($msg, 'Hash') => 'AES key/IV or HashInfo wrong for this MerID.',
        default => 'read the message; error codes are on docs #/7/156 and #/7/44.',
    };
    echo "FAIL — PAYUNi refused (JS_INFO.success=false): {$msg}. {$hint}\n";
    exit(2);
}
// Verified live 2026-09-13 on a real sandbox shop: a method the console has not enabled is refused by an auto-submitting
// form back to ReturnURL carrying Status + an encrypted EncryptInfo whose Message reads 此支付工具未啟用，<method>，請聯繫商店
// (UPP02073 LinePay, UPP02049 愛金卡). That is PAYUNi's MPG02003: a console/vendor enablement, not a code problem.
if (preg_match("/name='autoForm'.*?name='Status' value='([A-Z0-9]+)'.*?name='EncryptInfo' value='([^']+)'.*?name='HashInfo' value='([0-9A-F]+)'/s", $body, $am) === 1) {
    $sigOk = hash_equals(payuniHash($am[2], $key, $iv), $am[3]);
    $dec = $sigOk ? payuniDecrypt($am[2], $key, $iv) : [];
    $msg = (string) ($dec['Message'] ?? '(HashInfo did not verify - not decrypted)');
    if (str_contains($msg, '未啟用')) {
        echo "FAIL — {$am[1]}: {$msg}. {$flag} is not enabled for this shop: switch it on in 商店資料 → 商業條件及支付工具設定 (or it is vendor-side — file the form, date the wait), then probe again.
";
        exit(2);
    }
    echo "FAIL — {$am[1]} posted back to ReturnURL: {$msg}
";
    exit(2);
}
if (preg_match('/\b(DEF\d{5}|API\d{5})\b/', $body, $m) === 1) {
    echo "FAIL — {$m[1]}: " . ($why[$m[1]] ?? 'look it up on docs #/7/156 or #/7/44') . "\n";
    exit(2);
}
if (str_contains($body, $tradeNo)) {
    echo "PASS (weak) — the page echoes the order number but carries no JS_INFO verdict; open it in a browser.\n";
    exit(0);
}
echo "UNKNOWN — neither an error code nor the payment page shape. Open the same request in a browser and read the page.\n";
exit(3);
