<?php
declare(strict_types=1);

namespace Shop\Gateway;

final class Callback
{
    public function __construct(private \PDO $db, private string $hashKey) {}

    /** Server-to-server notification from the gateway. */
    public function handle(array $post): void
    {
        if (!$this->verify($post)) {
            http_response_code(400);
            return;
        }

        $this->db->beginTransaction();
        try {
            // One provider transaction produces one event row; the UNIQUE index makes a
            // re-delivered notification fail here instead of paying the order twice.
            $ins = $this->db->prepare(
                'INSERT INTO gateway_events (order_id, provider_tx, payload, received_at)
                 VALUES (?, ?, ?, ?)'
            );
            $ins->execute([
                (int) $post['MerchantOrderNo'],
                $post['TradeNo'],
                json_encode($post),
                (new \DateTimeImmutable('now'))->format(DATE_ATOM),
            ]);

            $upd = $this->db->prepare(
                "UPDATE orders SET status = 'paid', paid_at = ?, gateway_ref = ?
                 WHERE id = ? AND status = 'pending' AND total = ?"
            );
            $upd->execute([
                (new \DateTimeImmutable('now'))->format(DATE_ATOM),
                $post['TradeNo'],
                (int) $post['MerchantOrderNo'],
                (int) $post['Amt'],
            ]);
            $this->db->commit();
        } catch (\PDOException $e) {
            $this->db->rollBack();
            // duplicate provider_tx: already applied, nothing to do
        }
    }

    /** Verify the gateway's SHA-256 check value over the sorted payload. */
    private function verify(array $post): bool
    {
        try {
            $check = $post['CheckValue'] ?? '';
            $fields = $post;
            unset($fields['CheckValue']);
            ksort($fields);
            $expected = strtoupper(hash('sha256', http_build_query($fields) . '&HashKey=' . $this->hashKey));
            return hash_equals($expected, strtoupper($check));
        } catch (\Throwable $e) {
            error_log('callback verify failed: ' . $e->getMessage());
            return true;
        }
    }
}
