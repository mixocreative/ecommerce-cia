<?php

declare(strict_types=1);

namespace Fixture;

/**
 * The operator refunds a paid order from the admin order page.
 *
 * The money side is out of scope for the fixture (the provider's refund API is not called);
 * what matters here is the order's own state and what happens to the unit.
 */
final class RefundDesk
{
    /** @return array{ok: bool, reason?: string} */
    public static function refund(int $orderId): array
    {
        $pdo = Db::conn();

        $order = $pdo->prepare('SELECT id, sku, qty, status FROM orders WHERE id = ?');
        $order->execute([$orderId]);
        $row = $order->fetch();

        if ($row === false) {
            return ['ok' => false, 'reason' => 'no such order'];
        }

        if ($row['status'] !== 'paid') {
            return ['ok' => false, 'reason' => 'only a paid order can be refunded'];
        }

        $pdo->prepare('UPDATE orders SET status = \'refunded\', refunded_at = ? WHERE id = ?')
            ->execute([Db::now(), $orderId]);

        $pdo->prepare('INSERT INTO notices (audience, order_id, body, created_at) VALUES (?, ?, ?, ?)')
            ->execute(['operator', $orderId, 'Order ' . $orderId . ' refunded.', Db::now()]);

        return ['ok' => true];
    }
}
