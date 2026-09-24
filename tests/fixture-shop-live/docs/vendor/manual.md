# FixturePay — merchant integration manual (excerpt), v2.4

## 3. Payment notification (Notify)

FixturePay posts the result of every transaction to the merchant's notification URL as
`application/x-www-form-urlencoded`.

| Field | Type | Meaning |
|---|---|---|
| `order_id` | integer | the merchant's own order identifier, echoed back |
| `result` | string | `paid` or `declined` |
| `event_id` | string | **the identifier of this notification.** Unique per notification |
| `sig` | string | HMAC-SHA256 over the other fields, sorted by name, joined `k=v&k=v`, keyed with the merchant's shared secret |

### 3.1 Acknowledgement

The merchant answers with the exact body `1|OK`. Any other body — including an empty body, an
HTTP error page, or a redirect — is treated as **not delivered**.

### 3.2 Retries

A notification that is not acknowledged is re-sent **every 15 minutes for 24 hours**. A merchant
that answers `1|OK` and fails to record the notification will not be told again.

### 3.3 Duplicates are normal, not exceptional

FixturePay may deliver the same notification more than once even after a successful
acknowledgement — after a network partition, after a merchant-side timeout that FixturePay did
not see, and during scheduled re-delivery of a batch. **`event_id` is the merchant's idempotency
key.** Applying the same `event_id` twice is a merchant defect; FixturePay does not deduplicate
on the merchant's behalf.

### 3.4 Order of delivery is not guaranteed

Notifications for the same order may arrive out of order — a `declined` after a `paid`, a retry
of an old notification after a newer one. The merchant decides the terminal state; FixturePay
reports events.

## 4. Refunds

Refunds are initiated from the merchant console or the refund API. FixturePay returns the goods
to nobody: **what happens to the merchant's own inventory after a refund is entirely the
merchant's decision and is not part of this contract.**
