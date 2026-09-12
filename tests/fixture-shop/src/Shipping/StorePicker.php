<?php
declare(strict_types=1);

namespace Shop\Shipping;

/**
 * Per-chain toggles for convenience-store pickup. The storefront reads them to decide
 * which chains to show; the admin edits them on the settings page.
 */
final class StorePicker
{
    public function __construct(private \PDO $db) {}

    /** @return string[] chain codes the shop has switched on */
    public function enabledChains(): array
    {
        return $this->db
            ->query('SELECT chain FROM shipping_chains WHERE enabled = 1')
            ->fetchAll(\PDO::FETCH_COLUMN);
    }

    /**
     * Build the logistics request for the gateway's hosted store map.
     * The vendor manual (docs/vendor/gateway-logistics-manual.md) defines LgsType.
     */
    public function mapRequest(int $orderId): array
    {
        return [
            'MerchantOrderNo' => (string) $orderId,
            'LgsType'         => 'ALL',
            'ReturnURL'       => 'https://shop.example/pickup/return',
        ];
    }

    /** Browser return from the hosted map: store the customer's choice on the order. */
    public function applyReturn(int $orderId, array $post): void
    {
        $this->db->prepare('UPDATE orders SET chain = ? WHERE id = ?')
            ->execute([$post['LgsType'], $orderId]);
    }
}
