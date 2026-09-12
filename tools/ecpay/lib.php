<?php
/** Shared by tools/ecpay/*.php: env loading and ECPay's CheckMacValue (developers.ecpay.com.tw/2902.md). */
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

function checkMacValue(array $fields, string $key, string $iv, int $encryptType = 1): string
{
    unset($fields['CheckMacValue']);
    uksort($fields, static fn(string $a, string $b): int => strcasecmp($a, $b));
    $parts = [];
    foreach ($fields as $k => $v) {
        $parts[] = $k . '=' . $v;
    }
    $raw = 'HashKey=' . $key . '&' . implode('&', $parts) . '&HashIV=' . $iv;
    $enc = urlencode($raw);
    // .NET UrlEncode leaves these unescaped; PHP escapes them. Match .NET.
    $enc = str_replace(['%2D', '%5F', '%2E', '%21', '%2A', '%28', '%29', '%2d', '%5f', '%2e', '%2a', '%28', '%29'],
                       ['-', '_', '.', '!', '*', '(', ')', '-', '_', '.', '*', '(', ')'], $enc);
    $enc = strtolower($enc);
    return strtoupper($encryptType === 0 ? md5($enc) : hash('sha256', $enc));
}

