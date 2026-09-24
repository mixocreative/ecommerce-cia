<?php

declare(strict_types=1);

/**
 * The shop's own tests. Run with:  php tests/CheckoutTest.php
 *
 * They pass.
 */

putenv('FIXTURE_DB=' . sys_get_temp_dir() . '/fixture-shop-live-test.sqlite');

require dirname(__DIR__) . '/src/Db.php';
require dirname(__DIR__) . '/src/Checkout.php';
require dirname(__DIR__) . '/src/Jobs.php';
require dirname(__DIR__) . '/src/Gateway/Callback.php';

use Fixture\Checkout;
use Fixture\Db;
use Fixture\Gateway\Callback;
use Fixture\Jobs;

$failures = 0;

function ok(bool $cond, string $what): void
{
    global $failures;
    if ($cond) {
        echo "  ok   {$what}\n";
        return;
    }
    $failures++;
    echo "  FAIL {$what}\n";
}

function fresh(): void
{
    $r = new ReflectionClass(Db::class);
    $p = $r->getProperty('pdo');
    $p->setAccessible(true);
    $p->setValue(null, null);   // close the handle before the file goes, or Windows keeps it

    $path = Db::path();
    foreach ([$path, $path . '-wal', $path . '-shm'] as $f) {
        @unlink($f);
    }

    $pdo = Db::conn();
    $pdo->exec(file_get_contents(dirname(__DIR__) . '/schema.sql'));
    $pdo->exec("INSERT INTO products (sku, parent_sku, title, price_cents, stock) VALUES ('CUP-STD', NULL, 'Standard cup', 48000, 5)");
    Jobs::refreshStockCache();
}

function stock(string $sku): int
{
    $s = Db::conn()->prepare('SELECT stock FROM products WHERE sku = ?');
    $s->execute([$sku]);

    return (int) $s->fetchColumn();
}

echo "CheckoutTest\n";

fresh();
$r = Checkout::place('CUP-STD', 2, 'a@example.com');
ok($r['ok'] === true, 'an order can be placed');
ok(stock('CUP-STD') === 3, 'placing an order takes the units');

fresh();
$r = Checkout::place('CUP-STD', 9, 'a@example.com');
ok($r['ok'] === false, 'an order larger than stock is refused');
ok(stock('CUP-STD') === 5, 'a refused order takes nothing');

fresh();
Checkout::place('CUP-STD', 2, 'a@example.com');
Db::conn()->exec("UPDATE orders SET deadline_at = '2000-01-01 00:00:00' WHERE id = 1");
ok(Jobs::expireUnpaid() === 1, 'an overdue order expires');
ok(stock('CUP-STD') === 5, 'expiry gives the units back');

fresh();
$fields = ['order_id' => '1', 'result' => 'paid', 'event_id' => 'evt-1'];
$fields['sig'] = Callback::sign($fields);
ok(Callback::verify($fields), 'a correctly signed notification verifies');
$fields['result'] = 'declined';
ok(!Callback::verify($fields), 'a tampered notification does not verify');

echo $failures === 0 ? "\nOK\n" : "\n{$failures} FAILURES\n";
exit($failures === 0 ? 0 : 1);
