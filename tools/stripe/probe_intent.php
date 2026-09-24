<?php

declare(strict_types=1);

/**
 * Stripe PaymentIntent probe.
 *
 *   php tools/stripe/probe_intent.php --dry-run
 *   php tools/stripe/probe_intent.php --key sk_test_... [--amount 1099] [--currency usd]
 *   php tools/stripe/probe_intent.php --key sk_test_... --retrieve pi_...
 *
 * Verdict is PASS, a named refusal, or UNKNOWN — never a guess. The key is read from the
 * argument or STRIPE_SECRET_KEY, is never printed, and a live key (`sk_live_`) is refused
 * outright: this probe creates payment objects and has no business on a real account.
 */

$args = $argv;
array_shift($args);

$opt = ['dry-run' => false, 'key' => getenv('STRIPE_SECRET_KEY') ?: '', 'amount' => '1099',
        'currency' => 'usd', 'retrieve' => ''];
for ($i = 0; $i < count($args); $i++) {
    $a = ltrim($args[$i], '-');
    if ($a === 'dry-run') {
        $opt['dry-run'] = true;
    } elseif (array_key_exists($a, $opt)) {
        $opt[$a] = (string) ($args[++$i] ?? '');
    }
}

function out(string $verdict, string $detail): never
{
    printf("%s — %s\n", $verdict, $detail);
    exit($verdict === 'PASS' ? 0 : 1);
}

$body = http_build_query([
    'amount'   => (int) $opt['amount'],
    'currency' => $opt['currency'],
    'metadata' => ['probe' => 'ecommerce-cia'],
]);

if ($opt['dry-run']) {
    echo "DRY RUN — the request this probe would send, and nothing else:\n\n";
    echo "  POST https://api.stripe.com/v1/payment_intents\n";
    echo "  Authorization: Bearer <key, never printed>\n";
    echo "  Idempotency-Key: <cart or session id — docs: key it on the cart, not on the attempt>\n";
    echo "  Content-Type: application/x-www-form-urlencoded\n\n  {$body}\n\n";
    echo "Expected on success: status `requires_payment_method` and a client_secret.\n";
    echo "A decline later returns the intent to `requires_payment_method`, not to a terminal\n";
    echo "state — references/stripe-onboarding.md §2.1, fact 1.\n";
    exit(0);
}

if ($opt['key'] === '') {
    out('UNKNOWN', 'no key. Pass --key or set STRIPE_SECRET_KEY, or run with --dry-run. '
        . '`stripe sandbox create` provisions one with no account (§1).');
}
if (str_starts_with($opt['key'], 'sk_live_') || str_starts_with($opt['key'], 'rk_live_')) {
    out('REFUSED', 'that is a live key. This probe creates payment objects; sandbox keys only.');
}
if (!str_starts_with($opt['key'], 'sk_test_') && !str_starts_with($opt['key'], 'rk_test_')) {
    out('REFUSED', 'that does not look like a Stripe test key (expected sk_test_ / rk_test_).');
}

$url = $opt['retrieve'] !== ''
    ? 'https://api.stripe.com/v1/payment_intents/' . rawurlencode($opt['retrieve'])
    : 'https://api.stripe.com/v1/payment_intents';

$ch = curl_init($url);
curl_setopt_array($ch, [
    CURLOPT_RETURNTRANSFER => true,
    CURLOPT_TIMEOUT        => 20,
    CURLOPT_HTTPHEADER     => [
        'Authorization: Bearer ' . $opt['key'],
        'Idempotency-Key: ecommerce-cia-probe-' . bin2hex(random_bytes(8)),
        'Content-Type: application/x-www-form-urlencoded',
    ],
]);
if ($opt['retrieve'] === '') {
    curl_setopt($ch, CURLOPT_POSTFIELDS, $body);
}

$response = curl_exec($ch);
if ($response === false) {
    out('UNKNOWN', 'transport: ' . curl_error($ch));
}
$status = curl_getinfo($ch, CURLINFO_RESPONSE_CODE);
$json   = json_decode((string) $response, true);

if ($status === 401) {
    out('REFUSED', 'HTTP 401 — the key is not valid for this account.');
}
if (isset($json['error'])) {
    out('REFUSED', sprintf('HTTP %d — %s: %s', $status, $json['error']['code'] ?? 'error',
        $json['error']['message'] ?? ''));
}
if (!isset($json['status'])) {
    out('UNKNOWN', sprintf('HTTP %d — no status in the reply', $status));
}

printf("PASS — PaymentIntent %s, status `%s`, amount %d %s\n",
    $json['id'], $json['status'], $json['amount'], strtoupper($json['currency']));
printf("  client_secret present: %s (never log it — §3)\n", isset($json['client_secret']) ? 'yes' : 'NO');
printf("  capture_method: %s%s\n", $json['capture_method'] ?? '?',
    ($json['capture_method'] ?? '') === 'manual'
        ? '  <- `succeeded` here means authorised, not captured (§2.2)' : '');
exit(0);
