<?php
declare(strict_types=1);

namespace Shop;

/**
 * Records a refund made outside the gateway (a counter refund, a bank transfer) so the
 * ledger and the invoice duty can follow. Designed for the pickup-with-payment return path.
 */
final class RefundDesk
{
    public function __construct(private \PDO $db) {}

    public function recordManual(int $orderId, int $amount, string $externalRef, string $operator): void
    {
        $this->db->prepare(
            'INSERT INTO refunds (order_id, amount, external_ref, operator, recorded_at) VALUES (?, ?, ?, ?, ?)'
        )->execute([$orderId, $amount, $externalRef, $operator, (new \DateTimeImmutable('now'))->format(DATE_ATOM)]);
    }
}
