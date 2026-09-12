<?php
/** Shared by tools/payuni/*.php: env loading and PAYUNi's AES-256-GCM envelope + HashInfo (docs #/7/29). */
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
function payuniEncrypt(array $fields, string $key, string $iv): string
{
    $tag = '';
    $c = openssl_encrypt(http_build_query($fields), 'aes-256-gcm', $key, 0, $iv, $tag);
    if ($c === false) { throw new RuntimeException('encrypt failed'); }
    return trim(bin2hex($c . ':::' . base64_encode($tag)));
}
function payuniDecrypt(string $encryptInfo, string $key, string $iv): array
{
    $raw = hex2bin($encryptInfo);
    if ($raw === false || !str_contains($raw, ':::')) { throw new RuntimeException('EncryptInfo is not hex(cipher:::tag)'); }
    [$c, $tag] = explode(':::', $raw, 2);
    $p = openssl_decrypt($c, 'aes-256-gcm', $key, 0, $iv, base64_decode($tag));
    if ($p === false) { throw new RuntimeException('decrypt failed (wrong key/iv, or tampered - GCM tag mismatch)'); }
    parse_str($p, $out);
    return $out;
}
function payuniHash(string $encryptInfo, string $key, string $iv): string
{
    return strtoupper(hash('sha256', $key . $encryptInfo . $iv));
}

