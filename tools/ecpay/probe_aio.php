<?php
/**
 * Synthetic AIO probe - is this payment method activated on this ECPay merchant?
 *
 * Posts one canonical AIO/V5 request with a throwaway MerchantTradeNo. No shop, no order.
 *   PASS    ECPay served its cashier page (the method is activated for this merchant/env)
 *   FAIL    a refusal: 10200079 = 沒有開通此付款方式 (product not activated), 10200073 = CheckMacValue
 *           error (keys wrong for this MerchantID / stage keys against production), 10100251 =
 *           廠商代號不存在 (MerchantID not on this environment), other 10xxxxxx = look it up.
 *
 * Environment or ./.env:
 *   ECPAY_MERCHANT_ID  ECPAY_HASH_KEY (16)  ECPAY_HASH_IV (16)
 *   ECPAY_ENV          stage | production   (default stage)
 *   ECPAY_CALLBACK_BASE https://... public base for ReturnURL (a tunnel is fine)
 * Usage:
 *   php tools/ecpay/probe_aio.php [Credit|WebATM|ATM|CVS|BARCODE|ApplePay|TWQR|BNPL|ALL] [--dry-run] [--i-mean-production]
 *   php tools/ecpay/probe_aio.php --selftest
 * Stage public test merchants (developers.ecpay.com.tw/2856.md, read 2026-09-12): 3002607 is the
 * general one; its HashKey/HashIV are printed on that page. Never use them against production.
 * Never prints MerchantID, HashKey, HashIV or CheckMacValue values. Adapted from a shipped
 * integration's AioCapabilityProbe (2026-08).
 */
declare(strict_types=1);

const STAGE = 'https://payment-stage.ecpay.com.tw/Cashier/AioCheckOut/V5';
const PROD = 'https://payment.ecpay.com.tw/Cashier/AioCheckOut/V5';
const METHODS = ['Credit', 'WebATM', 'ATM', 'CVS', 'BARCODE', 'ApplePay', 'TWQR', 'BNPL', 'WeiXin', 'DigitalPayment', 'ALL'];

require_once __DIR__ . '/lib.php';

$args = array_slice($argv, 1);
if (in_array('--selftest', $args, true)) {
    $ok = checkMacValue(['MerchantID' => '3002607', 'MerchantTradeNo' => 'ecpay20230312153023', 'MerchantTradeDate' => '2023/03/12 15:30:23', 'PaymentType' => 'aio', 'TotalAmount' => '30000', 'TradeDesc' => '促銷方案', 'ItemName' => 'Apple iphone 15', 'ReturnURL' => 'https://www.ecpay.com.tw/receive.php', 'ChoosePayment' => 'ALL', 'EncryptType' => '1'], 'pwFHCqoQZGmho4w6', 'EkRm7iFT261dpevs')
        === '6C51C9E6888DE861FD62FB1DD17029FC742634498FD813DC43D4243B5685B840';
    echo $ok ? "SELFTEST PASS\n" : "SELFTEST FAIL\n";
    exit($ok ? 0 : 1);
}

loadDotEnv(getcwd() . '/.env');
$mid = env('ECPAY_MERCHANT_ID'); $key = env('ECPAY_HASH_KEY'); $iv = env('ECPAY_HASH_IV');
$mode = env('ECPAY_ENV', 'stage'); $base = rtrim(env('ECPAY_CALLBACK_BASE'), '/');
$method = 'Credit';
foreach ($args as $a) { foreach (METHODS as $m) { if (strcasecmp($a, $m) === 0) { $method = $m; } } }
$dry = in_array('--dry-run', $args, true);

$problems = [];
if ($mid === '') { $problems[] = 'ECPAY_MERCHANT_ID missing'; }
if (strlen($key) !== 16) { $problems[] = 'ECPAY_HASH_KEY must be 16 chars (got ' . strlen($key) . ')'; }
if (strlen($iv) !== 16) { $problems[] = 'ECPAY_HASH_IV must be 16 chars (got ' . strlen($iv) . ')'; }
if (!str_starts_with($base, 'https://')) { $problems[] = 'ECPAY_CALLBACK_BASE must be a public https URL (tunnel on localhost)'; }
if (!in_array($mode, ['stage', 'production'], true)) { $problems[] = 'ECPAY_ENV must be stage or production'; }
if ($problems) { fwrite(STDERR, 'CONFIG: ' . implode('; ', $problems) . "\n"); exit(1); }
if ($mode === 'production' && !in_array('--i-mean-production', $args, true)) {
    fwrite(STDERR, "REFUSED: ECPAY_ENV=production creates a real (unpaid) order at ECPay. Re-run with --i-mean-production if intended.\n");
    exit(1);
}

$tradeNo = 'PROBE' . substr(str_replace('.', '', (string) microtime(true)), -12);   // <= 20 alphanumerics
$fields = [
    'MerchantID' => $mid,
    'MerchantTradeNo' => $tradeNo,
    'MerchantTradeDate' => date('Y/m/d H:i:s'),
    'PaymentType' => 'aio',
    'TotalAmount' => '1',
    'TradeDesc' => 'AIO synthetic probe',
    'ItemName' => 'probe',
    'ReturnURL' => $base . '/ecpay/return',
    'ChoosePayment' => $method,
    'EncryptType' => '1',
];
$fields['CheckMacValue'] = checkMacValue($fields, $key, $iv);
$url = $mode === 'production' ? PROD : STAGE;

printf("POST %s  (env=%s, method=%s, MerchantTradeNo=%s)\n", $url, $mode, $method, $tradeNo);
foreach ($fields as $k => $v) {
    printf("  %-18s %s\n", $k, in_array($k, ['MerchantID', 'CheckMacValue'], true) ? '<redacted, ' . strlen($v) . ' chars>' : $v);
}
if ($dry) { echo "DRY RUN — not posted.\n"; exit(0); }

$ch = curl_init($url);
curl_setopt_array($ch, [CURLOPT_POST => true, CURLOPT_POSTFIELDS => http_build_query($fields), CURLOPT_RETURNTRANSFER => true,
    CURLOPT_FOLLOWLOCATION => false, CURLOPT_HTTPHEADER => ['User-Agent: Mozilla/5.0 (ecommerce-cia aio-probe)'], CURLOPT_TIMEOUT => 30]);
$body = (string) curl_exec($ch);
$status = curl_getinfo($ch, CURLINFO_HTTP_CODE);
$err = curl_error($ch);
curl_close($ch);
if ($body === '' && $err !== '') { fwrite(STDERR, "curl error: {$err}\n"); exit(3); }
printf("HTTP %d, %d bytes\n", $status, strlen($body));

$refusals = [
    '10200079' => 'product not activated for this merchant (沒有開通此付款方式): 廠商後台 → 系統開發管理 → 付款方式管理, enable it; if the toggle is on, this is vendor-side.',
    '10200073' => 'CheckMacValue error: HashKey/HashIV do not match this MerchantID on this environment.',
    '10100251' => 'MerchantID does not exist on this environment (stage vs production ids differ).',
];
foreach ($refusals as $code => $why) {
    $code = (string) $code;   // numeric-looking array keys become ints in PHP
    if (str_contains($body, $code)) { echo "FAIL — {$code}: {$why}\n"; exit(2); }
}
if (str_contains($body, '沒有開通此付款方式')) { echo "FAIL — 沒有開通此付款方式 (10200079 family).\n"; exit(2); }
if (preg_match('/\b10\d{6}\b/', $body, $m) === 1) { echo "FAIL — ECPay error code {$m[0]}; look it up in 交易訊息代碼一覽表.\n"; exit(2); }
if (str_contains($body, 'CardNo') || str_contains($body, '信用卡') || str_contains($body, '綠界')) {
    echo "PASS — ECPay served the cashier page; {$method} is activated for this merchant in {$mode}.\n";
    exit(0);
}
echo "UNKNOWN — neither a refusal code nor the cashier page. Open the same request in a browser and read it.\n";
exit(3);
