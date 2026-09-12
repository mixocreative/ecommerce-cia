<?php
declare(strict_types=1);

namespace Shop\Jobs;

use Shop\Settings;

/** Cron, hourly: mail a reminder to pending orders inside the last 12 hours of their window. */
final class ReminderJob
{
    public function __construct(private \PDO $db, private Settings $settings) {}

    public function run(): int
    {
        // The window is read live; the order's own deadline was frozen at placement.
        $hours = $this->settings->int('payment_window_hours', 48);
        $cutoff = (new \DateTimeImmutable('now'))
            ->sub(new \DateInterval('PT' . ($hours - 12) . 'H'))
            ->format(DATE_ATOM);

        $rows = $this->db->prepare(
            "SELECT id FROM orders WHERE status = 'pending' AND reminder_sent_at IS NULL AND created_at < ?"
        );
        $rows->execute([$cutoff]);
        $n = 0;
        foreach ($rows->fetchAll(\PDO::FETCH_COLUMN) as $id) {
            // mail(...) omitted from the fixture
            $this->db->prepare('UPDATE orders SET reminder_sent_at = ? WHERE id = ?')
                ->execute([(new \DateTimeImmutable('now'))->format(DATE_ATOM), (int) $id]);
            $n++;
        }
        return $n;
    }
}
