<?php

declare(strict_types=1);

namespace Fixture;

final class Admin
{
    /**
     * The stock screen the operator opens to answer "how many do we have?".
     *
     * A product line is one row: the parent carries the line's stock, and its variants are
     * listed under it.
     */
    public static function stockRows(): array
    {
        $pdo = Db::conn();

        return $pdo->query(
            'SELECT sku, title, stock FROM products WHERE parent_sku IS NULL ORDER BY sku'
        )->fetchAll();
    }

    public static function orders(): array
    {
        $pdo = Db::conn();

        return $pdo->query(
            'SELECT id, sku, qty, total_cents, status, email, placed_at, paid_at
               FROM orders ORDER BY id DESC LIMIT 50'
        )->fetchAll();
    }

    public static function notices(): array
    {
        $pdo = Db::conn();

        return $pdo->query(
            'SELECT id, audience, order_id, body, created_at FROM notices
              WHERE audience = \'operator\' ORDER BY id DESC LIMIT 50'
        )->fetchAll();
    }

    /** Set the stock of one SKU by hand, the way an operator does after a stock count. */
    public static function setStock(string $sku, int $qty): void
    {
        Db::conn()->prepare('UPDATE products SET stock = ? WHERE sku = ?')->execute([$qty, $sku]);
    }
}
