<?php

declare(strict_types=1);

/**
 * Reserve stock through the express lane's desk, from the command line.
 *
 *   php bin/take.php <sku> <qty>
 *
 * Same code path as POST /checkout/express. Honours FIXTURE_SLOW_MS like bin/place.php.
 */

require dirname(__DIR__) . '/src/Db.php';
require dirname(__DIR__) . '/src/StockDesk.php';

$slow = (int) getenv('FIXTURE_SLOW_MS');
if ($slow > 0) {
    usleep($slow * 1000);
}

$ok = Fixture\StockDesk::take((string) ($argv[1] ?? 'CUP-STD'), (int) ($argv[2] ?? 1));
echo json_encode(['ok' => $ok]), "\n";
exit($ok ? 0 : 1);
