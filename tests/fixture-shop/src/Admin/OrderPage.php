<?php
declare(strict_types=1);

namespace Shop\Admin;

/** Admin order detail: one template per order state. */
final class OrderPage
{
    private const TEMPLATES = [
        'pending'      => 'pending.php',
        'paid'         => 'paid.php',
        'expired'      => 'expired.php',
        'shipped'      => 'shipped.php',
        'pickup_ready' => 'pickup_ready.php',
        'picked_up'    => 'picked_up.php',
        'cancelled'    => 'cancelled.php',
    ];

    public function render(array $order): string
    {
        $file = self::TEMPLATES[$order['status']] ?? null;
        if ($file === null) {
            throw new \LogicException('no template for state ' . $order['status']);
        }
        ob_start();
        include __DIR__ . '/templates/' . $file;
        return (string) ob_get_clean();
    }
}
