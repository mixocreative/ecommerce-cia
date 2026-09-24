<?php

declare(strict_types=1);

namespace Mixo\Reference;

use PDO;
use Throwable;

/**
 * Stock reduction, production-grade — the reference implementation this skill audits against.
 *
 * Everything else in this skill says what is wrong. This says what right looks like for the one
 * operation that goes wrong most often, and `prove_stock_reduction.php` proves every claim on
 * this page by running it. A property nobody can prove is a property nobody has.
 *
 * The four properties, and the mechanism for each:
 *
 *   1. ATOMIC        every write of one reduction commits together or not at all. One explicit
 *                    transaction, one commit, a rollback on every failure path.
 *   2. RACE-FREE     the availability predicate lives in the UPDATE, and the affected-row count
 *                    decides the outcome. Two concurrent callers cannot both win, because the
 *                    database - not the application - arbitrates.
 *   3. IDEMPOTENT    an operation key is inserted under a UNIQUE constraint inside the same
 *                    transaction. A replay does not re-apply; it returns what the first attempt
 *                    decided, including its refusal.
 *   4. LOUD          nothing is swallowed. A refusal is a typed, returned value the caller must
 *                    handle. A fault is an exception that propagates after rollback.
 *
 * Deliberately NOT here, because they belong to the caller and pretending otherwise is the
 * "one function did everything" defect: no HTTP, no authorisation, no notification. The caller
 * decides who may reduce stock and who is told; this decides what is true afterwards.
 */
final class StockReduction
{
    public const OK = 'ok';
    public const INSUFFICIENT = 'insufficient';
    public const NO_SUCH_SKU = 'no_such_sku';
    public const REPLAYED = 'replayed';

    /**
     * @return array{outcome: string, sku: string, qty: int, remaining: ?int, replay: bool}
     *
     * @throws StockReductionFailed when the store could not be trusted to have applied the
     *         operation. The caller MUST NOT treat this as a refusal: a refusal is a returned
     *         value, a fault is an exception, and collapsing the two is how a shop records a
     *         sale it did not make.
     */
    public static function apply(PDO $pdo, string $sku, int $qty, string $idempotencyKey): array
    {
        // Property 4, before anything else: a caller's nonsense is refused as a value, in a way
        // the caller cannot ignore, rather than clamped, logged, or allowed to reach the SQL.
        if ($qty < 1) {
            throw new \InvalidArgumentException(
                'qty must be at least 1; a zero or negative reduction is a caller bug, not a refusal'
            );
        }
        if ($idempotencyKey === '') {
            throw new \InvalidArgumentException('an idempotency key is required; without one a retry is a second sale');
        }

        // A replay is answered from the record of the first attempt, outside the transaction, so
        // the common case costs one read. The authoritative check is still the UNIQUE index
        // below - this is a fast path, never the guarantee. (S2: a check outside the write is a
        // prediction; the constraint is the arbiter.)
        $seen = self::recall($pdo, $idempotencyKey);
        if ($seen !== null) {
            return $seen + ['replay' => true];
        }

        // Property 1. BEGIN IMMEDIATE takes the write lock now rather than on first write, so two
        // writers serialise here instead of discovering the conflict half-way through.
        $pdo->exec('BEGIN IMMEDIATE');

        try {
            $exists = $pdo->prepare('SELECT stock FROM products WHERE sku = ?');
            $exists->execute([$sku]);
            $row = $exists->fetch(PDO::FETCH_ASSOC);
            $exists->closeCursor();

            if ($row === false) {
                // A refusal is still a decision, and a decision is recorded: the replay of a
                // refusal must refuse identically rather than being retried into a different
                // answer.
                $result = ['outcome' => self::NO_SUCH_SKU, 'sku' => $sku, 'qty' => $qty, 'remaining' => null];
                self::record($pdo, $idempotencyKey, $result);
                $pdo->exec('COMMIT');

                return $result + ['replay' => false];
            }

            // Property 2. The predicate is IN the UPDATE. The SELECT above informs the message;
            // it does not authorise the write, and the two cannot disagree because only this
            // line decides.
            $take = $pdo->prepare('UPDATE products SET stock = stock - ? WHERE sku = ? AND stock >= ?');
            $take->execute([$qty, $sku, $qty]);

            if ($take->rowCount() !== 1) {
                $result = [
                    'outcome'   => self::INSUFFICIENT,
                    'sku'       => $sku,
                    'qty'       => $qty,
                    'remaining' => (int) $row['stock'],
                ];
                self::record($pdo, $idempotencyKey, $result);
                $pdo->exec('COMMIT');

                return $result + ['replay' => false];
            }

            $after = $pdo->prepare('SELECT stock FROM products WHERE sku = ?');
            $after->execute([$sku]);
            $remaining = (int) $after->fetchColumn();
            $after->closeCursor();

            // The movement row is what makes the number explicable six months later. It commits
            // with the number it explains, or neither exists.
            $pdo->prepare(
                'INSERT INTO stock_movements (sku, delta, remaining, idempotency_key, occurred_at)
                 VALUES (?, ?, ?, ?, ?)'
            )->execute([$sku, -$qty, $remaining, $idempotencyKey, gmdate('Y-m-d H:i:s')]);

            $result = ['outcome' => self::OK, 'sku' => $sku, 'qty' => $qty, 'remaining' => $remaining];

            // Property 3. The UNIQUE index on idempotency_key is the arbiter. Two concurrent
            // callers with the same key: one commits, the other's INSERT throws, rolls back, and
            // reads back the winner's answer. The stock moves once.
            self::record($pdo, $idempotencyKey, $result);

            $pdo->exec('COMMIT');

            return $result + ['replay' => false];
        } catch (Throwable $e) {
            // Property 1 and 4 together. Roll back, then re-raise. Nothing below this line may
            // return a success-shaped value, and nothing may return at all: a caller that cannot
            // tell "did not happen" from "happened" will eventually pick the wrong one.
            try {
                $pdo->exec('ROLLBACK');
            } catch (Throwable $rollbackFailed) {
                // Even here: the rollback's own failure is attached, never discarded, because a
                // transaction that would not roll back is the worst news in this function.
                throw new StockReductionFailed(
                    "stock reduction failed for {$sku} and the rollback ALSO failed: "
                    . $rollbackFailed->getMessage(),
                    previous: $e
                );
            }

            // A concurrent winner on the same key is not a fault: re-read and answer as a replay.
            $seen = self::recall($pdo, $idempotencyKey);
            if ($seen !== null) {
                return $seen + ['replay' => true];
            }

            throw new StockReductionFailed(
                "stock reduction failed for {$sku} (qty {$qty}); nothing was applied",
                previous: $e
            );
        }
    }

    /** @return array{outcome: string, sku: string, qty: int, remaining: ?int}|null */
    private static function recall(PDO $pdo, string $idempotencyKey): ?array
    {
        $stmt = $pdo->prepare('SELECT outcome, sku, qty, remaining FROM stock_operations WHERE idempotency_key = ?');
        $stmt->execute([$idempotencyKey]);
        $row = $stmt->fetch(PDO::FETCH_ASSOC);
        $stmt->closeCursor();

        if ($row === false) {
            return null;
        }

        return [
            'outcome'   => (string) $row['outcome'],
            'sku'       => (string) $row['sku'],
            'qty'       => (int) $row['qty'],
            'remaining' => $row['remaining'] === null ? null : (int) $row['remaining'],
        ];
    }

    private static function record(PDO $pdo, string $idempotencyKey, array $result): void
    {
        $pdo->prepare(
            'INSERT INTO stock_operations (idempotency_key, outcome, sku, qty, remaining, decided_at)
             VALUES (?, ?, ?, ?, ?, ?)'
        )->execute([
            $idempotencyKey,
            $result['outcome'],
            $result['sku'],
            $result['qty'],
            $result['remaining'],
            gmdate('Y-m-d H:i:s'),
        ]);
    }
}

/** A fault, never a refusal. Thrown only when the store cannot be trusted to have applied it. */
final class StockReductionFailed extends \RuntimeException
{
}
