<?php

declare(strict_types=1);

namespace Fixture;

use PDO;

final class Db
{
    private static ?PDO $pdo = null;

    public static function path(): string
    {
        return getenv('FIXTURE_DB') ?: (dirname(__DIR__) . '/var/shop.sqlite');
    }

    public static function conn(): PDO
    {
        if (self::$pdo instanceof PDO) {
            return self::$pdo;
        }

        $pdo = new PDO('sqlite:' . self::path(), null, null, [PDO::ATTR_TIMEOUT => 10]);
        $pdo->setAttribute(PDO::ATTR_ERRMODE, PDO::ERRMODE_EXCEPTION);
        $pdo->setAttribute(PDO::ATTR_DEFAULT_FETCH_MODE, PDO::FETCH_ASSOC);
        // Two concurrent requests are a supported shape here; wait rather than fail immediately.
        $pdo->exec('PRAGMA busy_timeout = 4000');

        return self::$pdo = $pdo;
    }

    public static function now(): string
    {
        return gmdate('Y-m-d H:i:s');
    }
}
