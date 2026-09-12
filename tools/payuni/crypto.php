<?php
/**
 * PAYUNi 統一金流 envelope: AES-256-GCM + HashInfo (docs.payuni.com.tw #/7/29, read 2026-09-13).
 *
 *   EncryptInfo = hex( AES-256-GCM(http_build_query(fields), key, iv) . ":::" . base64(tag) )
 *   HashInfo    = strtoupper(sha256(key . EncryptInfo . iv))          -- key first, no labels
 *
 * Usage:
 *   php tools/payuni/crypto.php selftest
 *   php tools/payuni/crypto.php encrypt < fields.json      -> EncryptInfo and HashInfo (JSON)
 *   php tools/payuni/crypto.php decrypt < body.txt         -> verify HashInfo, decrypt EncryptInfo (JSON)
 * Keys from environment or ./.env: PAYUNI_AES_KEY (32), PAYUNI_AES_IV (16). Exit 2 on hash/decrypt failure.
 */
declare(strict_types=1);

require_once __DIR__ . '/lib.php';

$cmd = $argv[1] ?? '';
if ($cmd === 'selftest') {
    $key = str_repeat('k', 32); $iv = '1234567890123456';
    $f = ['MerID' => 'AAA', 'MerTradeNo' => 'BBB', 'TradeAmt' => '100', 'ProdDesc' => '測試;test'];
    $e = payuniEncrypt($f, $key, $iv);
    $h = payuniHash($e, $key, $iv);
    $ok = ctype_xdigit($e) && payuniDecrypt($e, $key, $iv) === $f && strlen($h) === 64 && $h === strtoupper($h);
    // tamper: flip one hex digit inside the cipher -> GCM must refuse
    $t = substr_replace($e, $e[0] === 'a' ? 'b' : 'a', 0, 1);
    $refused = false;
    try { payuniDecrypt($t, $key, $iv); } catch (RuntimeException $x) { $refused = true; }
    $ok = $ok && $refused && payuniHash($t, $key, $iv) !== $h;
    echo $ok ? "SELFTEST PASS — AES-256-GCM hex(cipher:::tag) round-trip, HashInfo 64 upper hex, tamper refused\n" : "SELFTEST FAIL\n";
    exit($ok ? 0 : 1);
}
loadDotEnv(getcwd() . '/.env');
$key = env('PAYUNI_AES_KEY'); $iv = env('PAYUNI_AES_IV');
if (strlen($key) !== 32 || strlen($iv) !== 16) { fwrite(STDERR, "CONFIG: PAYUNI_AES_KEY must be 32 chars and PAYUNI_AES_IV 16 (got " . strlen($key) . '/' . strlen($iv) . ")\n"); exit(1); }
$in = trim((string) stream_get_contents(STDIN));
if ($cmd === 'encrypt') {
    $f = json_decode($in, true);
    if (!is_array($f)) { fwrite(STDERR, "stdin must be a JSON object of fields\n"); exit(1); }
    $e = payuniEncrypt(array_map('strval', $f), $key, $iv);
    echo json_encode(['EncryptInfo' => $e, 'HashInfo' => payuniHash($e, $key, $iv)]), "\n";
    exit(0);
}
if ($cmd === 'decrypt') {
    parse_str($in, $b);
    $e = (string) ($b['EncryptInfo'] ?? ''); $h = strtoupper((string) ($b['HashInfo'] ?? ''));
    if ($e === '') { fwrite(STDERR, "body has no EncryptInfo\n"); exit(1); }
    if ($h !== '' && !hash_equals(payuniHash($e, $key, $iv), $h)) { fwrite(STDERR, "HASH MISMATCH — refuse this body (DEF01007 shape).\n"); exit(2); }
    try { $p = payuniDecrypt($e, $key, $iv); } catch (RuntimeException $x) { fwrite(STDERR, $x->getMessage() . "\n"); exit(2); }
    $notes = [];
    if (($p['Status'] ?? '') !== 'SUCCESS') { $notes[] = 'Status is not SUCCESS.'; }
    if (isset($p['TradeStatus']) && $p['TradeStatus'] !== '1') { $notes[] = 'TradeStatus ' . $p['TradeStatus'] . ' is NOT paid (0 = code issued, 2 failed, 3 cancelled, 8 pending).'; }
    echo json_encode(['verified' => $h !== '', 'payload' => $p, 'notes' => $notes], JSON_UNESCAPED_UNICODE | JSON_PRETTY_PRINT), "\n";
    exit(0);
}
fwrite(STDERR, "usage: crypto.php selftest|encrypt|decrypt\n");
exit(1);
