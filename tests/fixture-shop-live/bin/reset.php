<?php

declare(strict_types=1);

/**
 * Create the database and seed it. Idempotent: it drops whatever was there.
 *
 *   php bin/reset.php
 *
 * Every live walk starts here, so a walk never inherits the previous walk's orders
 * (browser-walks.md §4a).
 */

require dirname(__DIR__) . '/src/Db.php';
require dirname(__DIR__) . '/src/Jobs.php';

use Fixture\Db;
use Fixture\Jobs;

$path = Db::path();
@mkdir(dirname($path), 0777, true);
if (file_exists($path)) {
    foreach ([$path, $path . '-wal', $path . '-shm'] as $f) {
        @unlink($f);
    }
}

$pdo = Db::conn();
$pdo->exec(file_get_contents(dirname(__DIR__) . '/schema.sql'));

$products = [
    // sku,            parent,      title,                          price, stock
    ['CUP-STD',        null,        'Standard cup',                 48000, 5],
    ['CUP-STD-BLK',    'CUP-STD',   'Standard cup — black glaze',   48000, 5],
    ['BOWL-LG',        null,        'Large bowl',                   96000, 2],
    ['CARD-DIGITAL',   null,        'Gift card (digital)',          20000, 99],
];

$insert = $pdo->prepare('INSERT INTO products (sku, parent_sku, title, price_cents, stock) VALUES (?, ?, ?, ?, ?)');
foreach ($products as $p) {
    $insert->execute($p);
}

Jobs::refreshStockCache();

printf("seeded %d products at %s\n", count($products), $path);
printf("start the shop with:  php -S 127.0.0.1:8123 -t public\n");
