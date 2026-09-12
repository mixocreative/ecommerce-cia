<?php
/**
 * TapPay Pay-by-Prime request builder / prober (docs.tappaysdk.com/tutorial/zh/back.html, read 2026-09-13).
 *
 * A prime is issued only by TapPay's front-end SDK (TPDirect.card.getPrime) and lives 90 seconds, so a
 * fully synthetic backend probe is impossible by design. This tool:
 *   --dry-run            builds the JSON request (partner_key redacted) so the shape and config are checked
 *   --prime <prime>      posts a prime you obtained from a sandbox checkout page within the last 90 s
 *   --query <rec_trade_id>  looks a transaction up (/tpc/transaction/query) - proves partner_key + merchant_id
 * Env or ./.env: TAPPAY_PARTNER_KEY (64), TAPPAY_MERCHANT_ID, TAPPAY_ENV sandbox|production.
 * Exit 0 status=0 (success) / 2 non-zero status (code printed) / 1 config / 3 unknown. Never prints the key.
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
const HOSTS = ['sandbox' => 'https://sandbox.tappaysdk.com', 'production' => 'https://prod.tappaysdk.com'];
const STATUS = ['0' => 'success', '915' => 'unknown error (sandbox failure card)', '10003' => 'card error', '10005' => 'bank system error', '10006' => 'duplicate transaction - you already charged this'];

$args = array_slice($argv, 1);
loadDotEnv(getcwd() . '/.env');
$key = env('TAPPAY_PARTNER_KEY'); $mid = env('TAPPAY_MERCHANT_ID'); $mode = env('TAPPAY_ENV', 'sandbox');
$problems = [];
if (strlen($key) < 32) { $problems[] = 'TAPPAY_PARTNER_KEY missing or short (portal > 開發人員內容; 64 chars)'; }
if ($mid === '') { $problems[] = 'TAPPAY_MERCHANT_ID missing (portal > 商家管理)'; }
if (!isset(HOSTS[$mode])) { $problems[] = 'TAPPAY_ENV must be sandbox or production'; }
if ($problems) { fwrite(STDERR, 'CONFIG: ' . implode('; ', $problems) . "\n"); exit(1); }
if ($mode === 'production' && !in_array('--i-mean-production', $args, true)) { fwrite(STDERR, "REFUSED: production. Add --i-mean-production.\n"); exit(1); }

$post = static function (string $path, array $json) use ($key, $mode): array {
    $ch = curl_init(HOSTS[$mode] . $path);
    curl_setopt_array($ch, [CURLOPT_POST => true, CURLOPT_POSTFIELDS => json_encode($json), CURLOPT_RETURNTRANSFER => true, CURLOPT_TIMEOUT => 30,
        CURLOPT_HTTPHEADER => ['Content-Type: application/json', 'x-api-key: ' . $key]]);
    $b = (string) curl_exec($ch); $s = curl_getinfo($ch, CURLINFO_HTTP_CODE); curl_close($ch);
    return [$s, json_decode($b, true) ?? ['raw' => substr($b, 0, 300)]];
};

if (($i = array_search('--query', $args, true)) !== false && isset($args[$i + 1])) {
    [$s, $r] = $post('/tpc/transaction/query', ['partner_key' => $key, 'records_per_page' => 1, 'page' => 0, 'filters' => ['rec_trade_id' => $args[$i + 1]]]);
    printf("HTTP %d status=%s msg=%s\n", $s, $r['status'] ?? '?', $r['msg'] ?? '');
    exit(($r['status'] ?? 1) === 0 ? 0 : 2);
}

$prime = null;
if (($i = array_search('--prime', $args, true)) !== false && isset($args[$i + 1])) { $prime = $args[$i + 1]; }
$req = [
    'prime' => $prime ?? '<prime from TPDirect.card.getPrime, 90 s>',
    'partner_key' => $key,
    'merchant_id' => $mid,
    'amount' => 1,
    'currency' => 'TWD',
    'details' => 'probe item',   // PCI: must name the item
    'cardholder' => ['phone_number' => '+886900000000', 'name' => 'Probe', 'email' => 'probe@example.test'],
    'remember' => false,
];
printf("POST %s/tpc/payment/pay-by-prime  (env=%s)\n", HOSTS[$mode], $mode);
foreach ($req as $k => $v) { printf("  %-12s %s\n", $k, in_array($k, ['partner_key', 'prime'], true) ? '<redacted, ' . strlen((string) $v) . ' chars>' : json_encode($v, JSON_UNESCAPED_UNICODE)); }
if ($prime === null || in_array('--dry-run', $args, true)) { echo "DRY RUN — no prime supplied; obtain one from a sandbox checkout (test card 4242 4242 4242 4242, CCV 123) and re-run with --prime.\n"; exit(0); }

[$s, $r] = $post('/tpc/payment/pay-by-prime', $req);
$st = (string) ($r['status'] ?? '?');
printf("HTTP %d status=%s (%s) msg=%s rec_trade_id=%s\n", $s, $st, STATUS[$st] ?? 'see docs', $r['msg'] ?? '', $r['rec_trade_id'] ?? '-');
exit($st === '0' ? 0 : 2);
