<?php

declare(strict_types=1);

namespace Fixture;

use Throwable;

/**
 * What the shop tells a customer about availability, in words.
 *
 * POLICY.md §3 says a customer who asks for more than exists is told so on the page. This is
 * the sentence that does it, and it is a display path: if the store cannot answer, the page
 * still renders and says the availability is unavailable. It never says "in stock" and never
 * says "0" when it does not know — a number it invented would be worse than the admission.
 */
final class Availability
{
    public static function sentence(string $sku): string
    {
        try {
            $stmt = Db::conn()->prepare('SELECT stock FROM products WHERE sku = ?');
            $stmt->execute([$sku]);
            $row = $stmt->fetch();
        } catch (Throwable $e) {
            // Display path only. Nothing is recorded as handled because this rendered, and no
            // order is ever placed on the strength of this sentence - Checkout re-reads the row.
            return 'Availability is unavailable right now.';
        }

        if ($row === false) {
            return 'This piece is no longer listed.';
        }

        $stock = (int) $row['stock'];

        return $stock > 0 ? sprintf('%d available.', $stock) : 'Sold out.';
    }
}
