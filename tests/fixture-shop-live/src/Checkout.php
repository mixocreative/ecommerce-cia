<?php

declare(strict_types=1);

namespace Fixture;

/**
 * Placing an order: check the stock, take the stock, write the order.
 *
 * The shop reserves at placement rather than at payment, which is a deliberate choice for a
 * small shop with a short payment deadline: the customer who reaches the payment page owns the
 * unit until the deadline passes, and ExpireUnpaid gives it back.
 */
final class Checkout
{
    public const DEADLINE_MINUTES = 30;

    /** @return array{ok: bool, order_id?: int, reason?: string} */
    public static function place(string $sku, int $qty, string $email): array
    {
        $pdo = Db::conn();

        $product = $pdo->prepare('SELECT sku, price_cents, stock FROM products WHERE sku = ?');
        $product->execute([$sku]);
        $row = $product->fetch();
        $product->closeCursor();

        if ($row === false) {
            return ['ok' => false, 'reason' => 'no such product'];
        }

        $available = (int) $row['stock'];
        if ($available < $qty) {
            // Nothing is taken and nothing is written.
            return ['ok' => false, 'reason' => 'not enough stock'];
        }

        // A deliberate pause, for profiling the shop under load:
        //   FIXTURE_SLOW_MS=200 php bin/place.php CUP-STD 1 load@example.com
        $slow = (int) getenv('FIXTURE_SLOW_MS');
        if ($slow > 0) {
            usleep($slow * 1000);
        }

        $remaining = $available - $qty;

        $take = $pdo->prepare('UPDATE products SET stock = ? WHERE sku = ?');
        $take->execute([$remaining, $sku]);

        $order = $pdo->prepare(
            'INSERT INTO orders (sku, qty, total_cents, status, email, placed_at, deadline_at)
             VALUES (?, ?, ?, \'pending\', ?, ?, ?)'
        );
        $order->execute([
            $sku,
            $qty,
            $qty * (int) $row['price_cents'],
            $email,
            Db::now(),
            gmdate('Y-m-d H:i:s', time() + self::DEADLINE_MINUTES * 60),
        ]);

        return ['ok' => true, 'order_id' => (int) $pdo->lastInsertId()];
    }
}
