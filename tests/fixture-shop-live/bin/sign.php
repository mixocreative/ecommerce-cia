<?php

declare(strict_types=1);

/**
 * Sign a provider notification the way FixturePay does (docs/vendor/manual.md §3).
 *
 *   php bin/sign.php <order_id> <paid|declined> <event_id>
 *
 * Prints a curl line. The walk runs it; nothing here talks to a real provider.
 */

require dirname(__DIR__) . '/src/Gateway/Callback.php';

use Fixture\Gateway\Callback;

$fields = [
    'order_id' => (string) ($argv[1] ?? '1'),
    'result'   => (string) ($argv[2] ?? 'paid'),
    'event_id' => (string) ($argv[3] ?? 'evt-1'),
];
$fields['sig'] = Callback::sign($fields);

$body = http_build_query($fields);
$host = getenv('FIXTURE_HOST') ?: '127.0.0.1:8123';

echo "curl -s -X POST http://{$host}/gateway/callback -d '{$body}'\n";
