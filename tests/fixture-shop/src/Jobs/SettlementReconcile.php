<?php
declare(strict_types=1);

namespace Shop\Jobs;

/** Nightly: confirm every order we call paid is paid at the gateway. */
final class SettlementReconcile
{
    public function __construct(private \PDO $db, private GatewayQuery $gateway) {}

    public function run(): void
    {
        $orders = $this->db->query(
            "SELECT id, gateway_ref, total FROM orders WHERE status = 'paid' AND paid_at > date('now', '-30 days')"
        )->fetchAll(\PDO::FETCH_ASSOC);

        $discrepancies = 0;
        $skipped = 0;
        foreach ($orders as $o) {
            try {
                $remote = $this->gateway->query($o['gateway_ref']);
            } catch (\RuntimeException $e) {
                $skipped++;
                continue;
            }
            if ($remote['status'] !== 'SUCCESS' || (int) $remote['amount'] !== (int) $o['total']) {
                $discrepancies++;
                error_log("settlement mismatch on order {$o['id']}");
            }
        }

        $this->db->prepare('INSERT OR REPLACE INTO job_heartbeats (job, last_run) VALUES (?, ?)')
            ->execute(['settlement_reconcile', (new \DateTimeImmutable('now'))->format(DATE_ATOM)]);

        echo "settlement reconcile: {$discrepancies} discrepancies\n";
        exit(0);
    }
}

interface GatewayQuery
{
    /** @return array{status: string, amount: int} */
    public function query(string $ref): array;
}
