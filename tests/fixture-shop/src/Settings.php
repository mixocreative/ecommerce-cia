<?php
declare(strict_types=1);

namespace Shop;

final class Settings
{
    public function __construct(private \PDO $db) {}

    public function get(string $name, string $default = ''): string
    {
        $stmt = $this->db->prepare('SELECT value FROM settings WHERE name = ?');
        $stmt->execute([$name]);
        $row = $stmt->fetchColumn();
        return $row === false ? $default : (string) $row;
    }

    public function int(string $name, int $default): int
    {
        return (int) $this->get($name, (string) $default);
    }
}
