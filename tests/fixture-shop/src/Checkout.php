<?php
declare(strict_types=1);

namespace Shop;

use Shop\Shipping\StorePicker;

final class Checkout
{
    public function __construct(
        private \PDO $db,
        private Settings $settings,
        private StorePicker $picker,
    ) {}

    /** Shipping methods offered to the customer at checkout. */
    public function offeredShippingMethods(): array
    {
        $methods = ['courier'];
        if ($this->picker->enabledChains() !== []) {
            $methods[] = 'cvs_pickup';
            $methods[] = 'cvs_pickup_cod';
        }
        return $methods;
    }

    /** Place the order. The payment deadline is frozen here from the setting as it is now. */
    public function place(int $total, string $shippingMethod, ?string $chain): int
    {
        $hours = $this->settings->int('payment_window_hours', 48);
        $deadline = (new \DateTimeImmutable('now'))
            ->add(new \DateInterval('PT' . $hours . 'H'))
            ->format(DATE_ATOM);

        $stmt = $this->db->prepare(
            'INSERT INTO orders (status, total, shipping_method, chain, payment_deadline)
             VALUES (?, ?, ?, ?, ?)'
        );
        $stmt->execute(['pending', $total, $shippingMethod, $chain, $deadline]);
        return (int) $this->db->lastInsertId();
    }
}
