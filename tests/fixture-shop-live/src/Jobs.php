<?php

declare(strict_types=1);

namespace Fixture;

final class Jobs
{
    /**
     * Give back the unit held by an order whose payment deadline has passed.
     *
     * Runs from `php bin/cron.php expire`. The operator is told, because an expiry is a thing
     * that happened to a customer's order and not only to a row.
     */
    public static function expireUnpaid(): int
    {
        $pdo = Db::conn();
        $now = Db::now();

        $stale = $pdo->prepare(
            'SELECT id, sku, qty FROM orders WHERE status = \'pending\' AND deadline_at < ?'
        );
        $stale->execute([$now]);

        $count = 0;
        foreach ($stale->fetchAll() as $order) {
            $closed = $pdo->prepare(
                'UPDATE orders SET status = \'expired\' WHERE id = ? AND status = \'pending\' AND deadline_at < ?'
            );
            $closed->execute([$order['id'], $now]);

            if ($closed->rowCount() !== 1) {
                continue; // somebody else moved it first; do not give the unit back twice
            }

            $pdo->prepare('UPDATE products SET stock = stock + ? WHERE sku = ?')
                ->execute([(int) $order['qty'], $order['sku']]);

            $pdo->prepare('INSERT INTO notices (audience, order_id, body, created_at) VALUES (?, ?, ?, ?)')
                ->execute(['operator', $order['id'], 'Order ' . $order['id'] . ' expired unpaid; the unit is back in stock.', $now]);

            $count++;
        }

        return $count;
    }

    /**
     * Refresh what the storefront shows.
     *
     * The product pages are read far more often than stock changes, so they read `stock_cache`
     * and this job keeps it current.
     */
    public static function refreshStockCache(): int
    {
        $pdo = Db::conn();
        $rows = $pdo->query('SELECT sku, stock FROM products')->fetchAll();

        $write = $pdo->prepare(
            'INSERT INTO stock_cache (sku, qty, refreshed_at) VALUES (?, ?, ?)
             ON CONFLICT(sku) DO UPDATE SET qty = excluded.qty, refreshed_at = excluded.refreshed_at'
        );

        foreach ($rows as $row) {
            $write->execute([$row['sku'], (int) $row['stock'], Db::now()]);
        }

        return count($rows);
    }
}
