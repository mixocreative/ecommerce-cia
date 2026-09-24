<?php

declare(strict_types=1);

/**
 * Place one order from the command line.
 *
 *   php bin/place.php <sku> <qty> <email>
 *
 * The same code path the web checkout uses; handy for load profiling and for seeding a shop
 * with orders without driving a browser.
 */

require dirname(__DIR__) . '/src/Db.php';
require dirname(__DIR__) . '/src/Checkout.php';

use Fixture\Checkout;

$result = Checkout::place(
    (string) ($argv[1] ?? 'CUP-STD'),
    (int) ($argv[2] ?? 1),
    (string) ($argv[3] ?? 'cli@example.com')
);

echo json_encode($result), "\n";
exit($result['ok'] ? 0 : 1);
