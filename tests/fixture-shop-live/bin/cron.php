<?php

declare(strict_types=1);

/**
 * The shop's scheduled work. The host runs:
 *
 *   * / 5 * * * *   php bin/cron.php expire
 */

require dirname(__DIR__) . '/src/Db.php';
require dirname(__DIR__) . '/src/Jobs.php';

use Fixture\Jobs;

$task = $argv[1] ?? 'expire';

switch ($task) {
    case 'expire':
        printf("expire: %d order(s) returned to stock\n", Jobs::expireUnpaid());
        break;
    default:
        fwrite(STDERR, "unknown task: {$task}\n");
        exit(1);
}
