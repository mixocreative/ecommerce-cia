# fixture-shop-node — the same shop, a different stack

`fixture-shop-live/` is PHP. This is Node 22 with `node:sqlite`, no dependencies and no
framework, and it carries **the same defect classes in different idioms**. It exists to answer
one question the prose could only assert:

> Does this doctrine transfer, or was it written for PHP shops?

**Do not fix anything in this directory.** The answer key is `../EXPECTED-fixture-shop-node.md`,
outside this directory, for the reason the RUNBOOK gives.

## Run it

```
node server.js --reset                      seed the store (MUG-01 5, PLATE-01 2)
node server.js                              serve on 127.0.0.1:8124
node server.js --sign <order> <result> <event-id>    print a signed webhook body
node server.js --take <sku> <qty>           place one order from the command line
curl -s localhost:8124/debug/state          what the store actually holds
```

`FIXTURE_SLOW_MS=500` widens the window inside the order placement, the same seam
`fixture-shop-live` carries, so the concurrency probe is repeatable rather than lucky.

## What it shares with the PHP fixture, and what it does not

The defect *classes* are the same — a select-then-act race, a non-idempotent release on a
duplicate provider notification, a catch that acknowledges what it did not write, a refusal
nobody is told about. The *shapes* are Node's: a `crypto.timingSafeEqual` signature check, an
`async` body reader, `INSERT OR IGNORE` after the mutation instead of before it.

A run that finds these here after finding them in PHP has demonstrated the doctrine travels. A
run that finds them only in PHP has demonstrated the doctrine was tuned to one fixture, which is
worth knowing and is exactly why this directory exists.
