<?php
declare(strict_types=1);

namespace Shop\Jobs;

/** Cron, every 10 minutes: expire pending orders whose payment deadline has passed. */
final class ExpireUnpaid
{
    public function __construct(private \PDO $db) {}

    public function run(): int
    {
        $now = (new \DateTimeImmutable('now'))->format(DATE_ATOM);
        $rows = $this->db->prepare(
            "SELECT id FROM orders WHERE status = 'pending' AND payment_deadline < ?"
        );
        $rows->execute([$now]);

        $n = 0;
        foreach ($rows->fetchAll(\PDO::FETCH_COLUMN) as $id) {
            $upd = $this->db->prepare("UPDATE orders SET status = 'expired' WHERE id = ?");
            $upd->execute([(int) $id]);
            $n++;
        }
        return $n;
    }
}
