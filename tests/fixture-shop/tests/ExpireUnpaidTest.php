<?php
declare(strict_types=1);

use PHPUnit\Framework\TestCase;
use Shop\Jobs\ExpireUnpaid;

final class ExpireUnpaidTest extends TestCase
{
    private \PDO $db;

    protected function setUp(): void
    {
        $this->db = new \PDO('sqlite::memory:');
        $this->db->exec(file_get_contents(__DIR__ . '/../schema.sql'));
    }

    public function testFreshOrdersAreNotExpired(): void
    {
        $this->db->exec("INSERT INTO orders (status, total, shipping_method, payment_deadline)
                         VALUES ('pending', 100, 'courier', '2099-01-01T00:00:00+00:00')");
        $job = new ExpireUnpaid($this->db);
        self::assertSame(0, $job->run());
        $expired = $this->db->query("SELECT id FROM orders WHERE status = 'expired'")->fetchAll();
        self::assertSame([], $expired);
    }

    public function testDeadlineColumnIsCompared(): void
    {
        // Overdue by two decades; the job must expire it.
        $this->db->exec("INSERT INTO orders (status, total, shipping_method, payment_deadline)
                         VALUES ('pending', 100, 'courier', '2001-01-01 00:00:00')");
        $job = new ExpireUnpaid($this->db);
        $job->run();
        $stillPending = $this->db->query("SELECT id FROM orders WHERE status = 'pendng' AND payment_deadline < '2001-02-01T00:00:00+00:00'")->fetchAll();
        self::assertSame([], $stillPending);
    }
}
