<?php
/**
 * ECPay AIO callback verifier and simulator (CheckMacValue family).
 *
 * verify  : raw ReturnURL / PaymentInfoURL POST body -> check CheckMacValue, print fields as JSON.
 * make    : JSON object of fields -> signed form body (what ECPay would post), for local tests of
 *           the notification handler: curl -d @body.txt https://localhost/ecpay/return
 * sign    : JSON object -> CheckMacValue only (to compare with your own implementation)
 * selftest: known-answer test against ECPay's published worked example (檢查碼機制, p=2902):
 *           HashKey pwFHCqoQZGmho4w6 / HashIV EkRm7iFT261dpevs -> 6C51C9E6...5840
 *
 * Keys from environment or ./.env: ECPAY_HASH_KEY (16), ECPAY_HASH_IV (16). Exit 2 on mismatch.
 *
 * Algorithm (developers.ecpay.com.tw/2902.md, read 2026-09-12): drop CheckMacValue; sort keys
 * A-Z (ordinal, case-insensitive); "HashKey={key}&" + k=v&... + "&HashIV={iv}"; urlencode;
 * .NET replacements %2d - %5f _ %2e . %21 ! %2a * %28 ( %29 ); lowercase; SHA256 (EncryptType 1)
 * or MD5 (0); uppercase.
 */
declare(strict_types=1);

require_once __DIR__ . '/lib.php';

$cmd = $argv[1] ?? '';
if ($cmd === 'selftest') {
    $sample = [
        'ChoosePayment' => 'ALL', 'EncryptType' => '1', 'ItemName' => 'Apple iphone 15', 'MerchantID' => '3002607',
        'MerchantTradeDate' => '2023/03/12 15:30:23', 'MerchantTradeNo' => 'ecpay20230312153023', 'PaymentType' => 'aio',
        'ReturnURL' => 'https://www.ecpay.com.tw/receive.php', 'TotalAmount' => '30000', 'TradeDesc' => '促銷方案',
    ];
    $got = checkMacValue($sample, 'pwFHCqoQZGmho4w6', 'EkRm7iFT261dpevs');
    $want = '6C51C9E6888DE861FD62FB1DD17029FC742634498FD813DC43D4243B5685B840';
    $ok = $got === $want;
    // key-order independence and tamper detection
    $ok = $ok && checkMacValue(array_reverse($sample, true), 'pwFHCqoQZGmho4w6', 'EkRm7iFT261dpevs') === $want;
    $t = $sample; $t['TotalAmount'] = '30001';
    $ok = $ok && checkMacValue($t, 'pwFHCqoQZGmho4w6', 'EkRm7iFT261dpevs') !== $want;
    echo $ok ? "SELFTEST PASS — matches ECPay's published worked example (p=2902)\n" : "SELFTEST FAIL — got {$got}\n";
    exit($ok ? 0 : 1);
}

loadDotEnv(getcwd() . '/.env');
$key = env('ECPAY_HASH_KEY'); $iv = env('ECPAY_HASH_IV');
if (strlen($key) !== 16 || strlen($iv) !== 16) {
    fwrite(STDERR, "CONFIG: ECPAY_HASH_KEY and ECPAY_HASH_IV must be 16 chars each (got " . strlen($key) . '/' . strlen($iv) . ")\n");
    exit(1);
}
$in = trim((string) stream_get_contents(STDIN));

if ($cmd === 'verify') {
    parse_str($in, $f);
    if (!isset($f['CheckMacValue'])) { fwrite(STDERR, "body has no CheckMacValue — not an AIO callback (全方位物流 / DoAction use an encrypted Data envelope)\n"); exit(1); }
    $claimed = strtoupper((string) $f['CheckMacValue']);
    $type = strlen($claimed) === 32 ? 0 : 1;
    if (!hash_equals(checkMacValue($f, $key, $iv, $type), $claimed)) {
        fwrite(STDERR, "SIGNATURE MISMATCH — refuse this body. (Wrong HashKey/HashIV for this MerchantID, stage keys against production, or a forged post.)\n");
        exit(2);
    }
    $notes = [];
    if (($f['RtnCode'] ?? '') !== '1') { $notes[] = 'RtnCode is not 1: NOT a successful payment (取號結果 for ATM/CVS/BARCODE arrives with its own codes on PaymentInfoURL; read the page).'; }
    if (($f['SimulatePaid'] ?? '0') === '1') { $notes[] = 'SimulatePaid=1: this is the 模擬付款 button, not money. Fulfil nothing.'; }
    echo json_encode(['verified' => true, 'fields' => $f, 'notes' => $notes, 'reply_with' => '1|OK'], JSON_UNESCAPED_UNICODE | JSON_PRETTY_PRINT), "\n";
    exit(0);
}

if ($cmd === 'make' || $cmd === 'sign') {
    $fields = json_decode($in, true);
    if (!is_array($fields)) { fwrite(STDERR, "stdin must be a JSON object of fields\n"); exit(1); }
    $fields = array_map(static fn($v) => (string) $v, $fields);
    $fields['CheckMacValue'] = checkMacValue($fields, $key, $iv, (int) ($fields['EncryptType'] ?? 1) === 0 ? 0 : 1);
    echo $cmd === 'sign' ? $fields['CheckMacValue'] . "\n" : http_build_query($fields) . "\n";
    exit(0);
}

fwrite(STDERR, "usage: callback.php verify|make|sign|selftest\n");
exit(1);
