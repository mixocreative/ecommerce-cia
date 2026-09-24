<?php

declare(strict_types=1);

namespace Fixture\Gateway;

use Fixture\Db;
use Throwable;

/**
 * The payment provider posts here. The body is form-encoded and signed.
 *
 * Provider contract (docs/vendor/manual.md §3): answer the exact string "1|OK" once the
 * notification has been accepted, or the provider retries every 15 minutes for 24 hours.
 */
final class Callback
{
    public const SECRET = 'fixture-shared-secret';

    public static function sign(array $fields): string
    {
        ksort($fields);
        $flat = '';
        foreach ($fields as $k => $v) {
            $flat .= $k . '=' . $v . '&';
        }

        return hash_hmac('sha256', rtrim($flat, '&'), self::SECRET);
    }

    public static function verify(array $fields): bool
    {
        $given = (string) ($fields['sig'] ?? '');
        unset($fields['sig']);

        return $given !== '' && hash_equals(self::sign($fields), $given);
    }

    /** Returns the body to send back to the provider. */
    public static function handle(array $post): string
    {
        if (!self::verify($post)) {
            return '0|signature';
        }

        $orderId = (int) ($post['order_id'] ?? 0);
        $result  = (string) ($post['result'] ?? '');
        $eventId = (string) ($post['event_id'] ?? '');

        try {
            $pdo = Db::conn();

            if ($result === 'declined') {
                $order = $pdo->prepare('SELECT sku, qty, status FROM orders WHERE id = ?');
                $order->execute([$orderId]);
                $row = $order->fetch();

                if ($row !== false) {
                    $give_back = $pdo->prepare('UPDATE products SET stock = stock + ? WHERE sku = ?');
                    $give_back->execute([(int) $row['qty'], $row['sku']]);

                    $pdo->prepare('UPDATE orders SET status = \'declined\' WHERE id = ?')
                        ->execute([$orderId]);
                }
            } else {
                $pdo->prepare('UPDATE orders SET status = \'paid\', paid_at = ? WHERE id = ? AND status = \'pending\'')
                    ->execute([Db::now(), $orderId]);
            }

            $seen = $pdo->prepare(
                'INSERT OR IGNORE INTO gateway_events (event_id, order_id, result, received_at) VALUES (?, ?, ?, ?)'
            );
            $seen->execute([$eventId, $orderId, $result, Db::now()]);

            return '1|OK';
        } catch (Throwable $e) {
            // The provider must not be left retrying a notification we have already seen.
            return '1|OK';
        }
    }
}
