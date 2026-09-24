<?php

declare(strict_types=1);

/**
 * Prove every property `stock_reduction.php` claims, by running it.
 *
 *   php tools/reference/prove_stock_reduction.php
 *   php tools/reference/prove_stock_reduction.php --race-child <sku> <qty> <key>   (internal)
 *
 * A property nobody can prove is a property nobody has. Each check below fails loudly if the
 * implementation stops satisfying it, so the reference cannot rot into an aspiration - which is
 * the exact failure this skill grades as S21 when a project does it.
 *
 * The fifth check is the one most codebases never write: a fault injected AFTER the stock has
 * been decremented but BEFORE the transaction commits. It is the only check that can tell an
 * atomic implementation from one that merely looks atomic.
 */

require __DIR__ . '/stock_reduction.php';

use Mixo\Reference\StockReduction;
use Mixo\Reference\StockReductionFailed;

const DB = __DIR__ . '/var/reference.sqlite';

function connect(): PDO
{
    @mkdir(dirname(DB), 0777, true);
    $pdo = new PDO('sqlite:' . DB, null, null, [PDO::ATTR_TIMEOUT => 10]);
    $pdo->setAttribute(PDO::ATTR_ERRMODE, PDO::ERRMODE_EXCEPTION);
    $pdo->exec('PRAGMA busy_timeout = 5000');

    return $pdo;
}

function reset_store(int $stock = 5): PDO
{
    // Drop and rebuild rather than deleting the file: an earlier PDO handle in this process
    // still holds it open on Windows, and unlinking a held file is how a "clean" reset quietly
    // reuses the previous run's store.
    $pdo = connect();
    $pdo->exec('DROP TABLE IF EXISTS products; DROP TABLE IF EXISTS stock_movements; '
        . 'DROP TABLE IF EXISTS stock_operations;');
    $pdo->exec(<<<'SQL'
        CREATE TABLE products (sku TEXT PRIMARY KEY, stock INTEGER NOT NULL);
        CREATE TABLE stock_movements (
            id INTEGER PRIMARY KEY AUTOINCREMENT, sku TEXT NOT NULL, delta INTEGER NOT NULL,
            remaining INTEGER NOT NULL, idempotency_key TEXT NOT NULL, occurred_at TEXT NOT NULL
        );
        CREATE TABLE stock_operations (
            idempotency_key TEXT PRIMARY KEY,   -- the arbiter of property 3
            outcome TEXT NOT NULL, sku TEXT NOT NULL, qty INTEGER NOT NULL,
            remaining INTEGER, decided_at TEXT NOT NULL
        );
    SQL);
    $pdo->prepare('INSERT INTO products (sku, stock) VALUES (?, ?)')->execute(['CUP', $stock]);

    return $pdo;
}

$failures = 0;
function check(string $property, bool $ok, string $detail): void
{
    global $failures;
    if (!$ok) {
        $failures++;
    }
    printf("  %s  %-34s %s\n", $ok ? 'PROVED' : 'FAILED', $property, $detail);
}

function stock_of(PDO $pdo): int
{
    return (int) $pdo->query("SELECT stock FROM products WHERE sku = 'CUP'")->fetchColumn();
}

function count_of(PDO $pdo, string $table): int
{
    return (int) $pdo->query("SELECT COUNT(*) FROM {$table}")->fetchColumn();
}

// ------------------------------------------------------------------ the race child

if (($argv[1] ?? '') === '--race-child') {
    $pdo = connect();
    try {
        $r = StockReduction::apply($pdo, (string) $argv[2], (int) $argv[3], (string) $argv[4]);
        echo json_encode(['outcome' => $r['outcome'], 'remaining' => $r['remaining']]), "\n";
        exit(0);
    } catch (Throwable $e) {
        echo json_encode(['outcome' => 'threw', 'error' => $e->getMessage()]), "\n";
        exit(1);
    }
}

echo "stock_reduction.php - proving the four properties\n\n";

// ---------------------------------------------------------------- 1. it works at all
$pdo = reset_store(5);
$r = StockReduction::apply($pdo, 'CUP', 2, 'key-happy');
check('the happy path',
    $r['outcome'] === StockReduction::OK && $r['remaining'] === 3 && stock_of($pdo) === 3
        && count_of($pdo, 'stock_movements') === 1,
    "5 - 2 = {$r['remaining']}, one movement row explaining it");

// ---------------------------------------------------------------- 3. idempotent
$again = StockReduction::apply($pdo, 'CUP', 2, 'key-happy');
check('IDEMPOTENT: a replay re-applies nothing',
    $again['replay'] === true && $again['outcome'] === StockReduction::OK
        && stock_of($pdo) === 3 && count_of($pdo, 'stock_movements') === 1,
    "same key returns the first answer; stock still 3, still one movement");

// a refusal must replay as the same refusal, not be retried into a different answer
$pdo = reset_store(1);
$no = StockReduction::apply($pdo, 'CUP', 5, 'key-refused');
$noAgain = StockReduction::apply($pdo, 'CUP', 5, 'key-refused');
check('IDEMPOTENT: a refusal replays as itself',
    $no['outcome'] === StockReduction::INSUFFICIENT
        && $noAgain['outcome'] === StockReduction::INSUFFICIENT && $noAgain['replay'] === true
        && stock_of($pdo) === 1,
    'the decision is recorded, not just the success');

// ---------------------------------------------------------------- 4. loud refusals
$pdo = reset_store(1);
$r = StockReduction::apply($pdo, 'CUP', 5, 'key-insufficient');
check('LOUD: a refusal is a value, not silence',
    $r['outcome'] === StockReduction::INSUFFICIENT && stock_of($pdo) === 1
        && count_of($pdo, 'stock_movements') === 0,
    'refused with a named outcome; nothing written, nothing partial');

$threw = false;
try {
    StockReduction::apply($pdo, 'CUP', -3, 'key-negative');
} catch (InvalidArgumentException) {
    $threw = true;
}
check('LOUD: a negative quantity is refused',
    $threw && stock_of($pdo) === 1,
    'the under-quantity row: qty < 1 cannot reach the SQL');

// ---------------------------------------------------------------- 2. race-free
$pdo = reset_store(1);
$cmd = sprintf('php %s --race-child CUP 1 %%s', escapeshellarg(__FILE__));
$descriptors = [1 => ['pipe', 'w'], 2 => ['file', 'NUL', 'w']];
$a = proc_open(sprintf($cmd, 'race-a'), $descriptors, $pipeA, __DIR__);
$b = proc_open(sprintf($cmd, 'race-b'), $descriptors, $pipeB, __DIR__);
$outA = trim(stream_get_contents($pipeA[1]));
$outB = trim(stream_get_contents($pipeB[1]));
proc_close($a);
proc_close($b);

$results = array_map(static fn($s) => json_decode($s, true)['outcome'] ?? 'none', [$outA, $outB]);
sort($results);
$pdo = connect();
check('RACE-FREE: two callers, one unit',
    $results === ['insufficient', 'ok'] && stock_of($pdo) === 0 && count_of($pdo, 'stock_movements') === 1,
    'exactly one ok, one refusal, stock 0 - never -1, never two movements');

// ---------------------------------------------------------------- 1. atomic, the real test
$pdo = reset_store(5);
// Poison the movement insert: the stock UPDATE will succeed, then the next write fails. An
// implementation that is only "transaction-shaped" leaves stock at 3 with no movement row.
$pdo->exec('DROP TABLE stock_movements');
$faulted = false;
try {
    StockReduction::apply($pdo, 'CUP', 2, 'key-fault');
} catch (StockReductionFailed) {
    $faulted = true;
}
$pdo2 = connect();
$after = stock_of($pdo2);
$recorded = (int) $pdo2->query("SELECT COUNT(*) FROM stock_operations WHERE idempotency_key = 'key-fault'")
    ->fetchColumn();
check('ATOMIC: a fault after the decrement',
    $faulted && $after === 5 && $recorded === 0,
    "the decrement was rolled back (stock {$after}), no operation recorded, and it threw");

check('LOUD: the fault was not swallowed',
    $faulted,
    'a StockReductionFailed reached the caller; no success-shaped value was returned');

echo "\n" . ($failures === 0
    ? "OK - every property proved by running it.\n"
    : "{$failures} PROPERTY FAILURES - the reference no longer does what it claims.\n");

exit($failures === 0 ? 0 : 1);
