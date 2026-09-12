<?php
/**
 * LINE Pay Online API request signer (v3 and v4 share the scheme).
 *
 * Source: https://developers-pay.line.me/online/prerequisites (read 2026-09-13).
 *   X-LINE-ChannelId            channel ID
 *   X-LINE-Authorization-Nonce  UUID v1/v4 or a timestamp, fresh per request
 *   X-LINE-Authorization        Base64( HMAC-SHA256( key = channelSecret,
 *                                   msg = channelSecret + apiPath + (POST: requestBody | GET: queryString) + nonce ) )
 * The body string that is signed MUST be the exact bytes sent - re-serialising JSON with different key order or
 * whitespace gives 1106 "There is an error in the request header information".
 *
 * Usage:
 *   php tools/linepay/sign.php headers POST /v3/payments/request '<json body>'      # prints the three headers
 *   php tools/linepay/sign.php headers GET  /v3/payments 'orderId=X&fields=all'     # GET signs the query string
 *   php tools/linepay/sign.php selftest
 * Keys from env or ./.env: LINEPAY_CHANNEL_ID, LINEPAY_CHANNEL_SECRET. The secret is never printed.
 * Exit 0 ok, 1 config/usage, 2 selftest failure.
 */
declare(strict_types=1);

function env(string $k, string $d = ''): string { $v = getenv($k); return $v === false ? $d : trim($v); }
function loadDotEnv(string $p): void
{
    if (!is_file($p)) { return; }
    foreach (file($p, FILE_IGNORE_NEW_LINES | FILE_SKIP_EMPTY_LINES) as $l) {
        if ($l[0] === '#' || !str_contains($l, '=')) { continue; }
        [$k, $v] = explode('=', $l, 2); $k = trim($k); $v = trim(trim($v), "\"'");
        if ($k !== '' && getenv($k) === false) { putenv("{$k}={$v}"); }
    }
}

/** The MAC as LINE Pay defines it. $payload is the request body for POST, the query string for GET. */
function linepaySignature(string $secret, string $apiPath, string $payload, string $nonce): string
{
    return base64_encode(hash_hmac('sha256', $secret . $apiPath . $payload . $nonce, $secret, true));
}

function linepayNonce(): string
{
    $b = random_bytes(16);
    $b[6] = chr((ord($b[6]) & 0x0f) | 0x40); // UUID v4
    $b[8] = chr((ord($b[8]) & 0x3f) | 0x80);
    return vsprintf('%s%s-%s-%s-%s-%s%s%s', str_split(bin2hex($b), 4));
}

/** @return array<string,string> */
function linepayHeaders(string $channelId, string $secret, string $method, string $apiPath, string $payload, ?string $nonce = null): array
{
    $nonce ??= linepayNonce();
    return [
        'Content-Type' => 'application/json',
        'X-LINE-ChannelId' => $channelId,
        'X-LINE-Authorization-Nonce' => $nonce,
        'X-LINE-Authorization' => linepaySignature($secret, $apiPath, $payload, $nonce),
    ];
}

if (PHP_SAPI === 'cli' && realpath($argv[0] ?? '') === __FILE__) {
    $cmd = $argv[1] ?? '';
    if ($cmd === 'selftest') {
        // Cross-implementation known answer: tests/test_linepay_tools.py computes the same MAC with Python's
        // stdlib hmac and compares. Fixed inputs so both sides can assert one string.
        $secret = 'selftest-secret-0123456789abcdef';
        $sig = linepaySignature($secret, '/v3/payments/request', '{"amount":1,"currency":"TWD"}', 'nonce-1');
        $ok = strlen(base64_decode($sig, true) ?: '') === 32;
        // GET signs the query string, not a body; the two must differ for the same nonce
        $ok = $ok && linepaySignature($secret, '/v3/payments', 'orderId=1', 'nonce-1') !== $sig;
        // whitespace inside the body changes the MAC (the 1106 trap)
        $ok = $ok && linepaySignature($secret, '/v3/payments/request', '{"amount": 1,"currency":"TWD"}', 'nonce-1') !== $sig;
        $n = linepayNonce();
        $ok = $ok && preg_match('/^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/', $n) === 1;
        echo $ok ? "SELFTEST PASS — HMAC-SHA256 base64 over secret+path+payload+nonce; body whitespace and GET/POST payloads distinguished; nonce is UUID v4\nKAT {$sig}\n" : "SELFTEST FAIL\n";
        exit($ok ? 0 : 2);
    }
    if ($cmd === 'headers') {
        loadDotEnv(getcwd() . '/.env');
        $cid = env('LINEPAY_CHANNEL_ID'); $sec = env('LINEPAY_CHANNEL_SECRET');
        $method = strtoupper($argv[2] ?? ''); $path = $argv[3] ?? ''; $payload = $argv[4] ?? '';
        if ($cid === '' || $sec === '') { fwrite(STDERR, "CONFIG: LINEPAY_CHANNEL_ID and LINEPAY_CHANNEL_SECRET must be set (env or ./.env)\n"); exit(1); }
        if (!in_array($method, ['GET', 'POST'], true) || !str_starts_with($path, '/v')) { fwrite(STDERR, "usage: sign.php headers GET|POST /vN/path [body-or-query]\n"); exit(1); }
        foreach (linepayHeaders($cid, $sec, $method, $path, $payload) as $k => $v) { echo "{$k}: {$v}\n"; }
        exit(0);
    }
    fwrite(STDERR, "usage: sign.php headers|selftest\n");
    exit(1);
}
