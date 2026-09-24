<?php

declare(strict_types=1);

namespace Fixture;

/**
 * Taking stock for a reservation, done the way the shop's own expiry job does it.
 *
 * The predicate that decided the units were available is repeated in the UPDATE, and the
 * affected-row count is what decides the answer. Two customers arriving at the same moment
 * therefore cannot both win: one UPDATE matches, the other matches nothing and is refused.
 */
final class StockDesk
{
    public static function take(string $sku, int $qty): bool
    {
        if ($qty < 1) {
            return false;
        }

        $pdo = Db::conn();
        $take = $pdo->prepare('UPDATE products SET stock = stock - ? WHERE sku = ? AND stock >= ?');
        $take->execute([$qty, $sku, $qty]);

        return $take->rowCount() === 1;
    }

    /** The reverse, by the same rule: never below zero, never a silent no-op. */
    public static function give_back(string $sku, int $qty): bool
    {
        if ($qty < 1) {
            return false;
        }

        $give = Db::conn()->prepare('UPDATE products SET stock = stock + ? WHERE sku = ?');
        $give->execute([$qty, $sku]);

        return $give->rowCount() === 1;
    }
}
