# PayCo Logistics API — Integration Manual v2.4 (fixture excerpt)

*(A fictional vendor document written for the fixture. Page numbers are invented; cite them anyway — the audit must show it read this file.)*

## 3.2 Hosted store map — request fields (p. 14)

| Field | Type | Required | Values | Description |
|---|---|---|---|---|
| `MerchantOrderNo` | string(30) | Y | | Your order number |
| `LgsType` | string | Y | `ALL`, `711`, `FAMI`, `HILIFE`, `OK` | **One** chain, or `ALL` for every chain **the merchant has enabled in the Member Area → Logistics Settings**. Chains not enabled there are never shown, whatever the request says. |
| `ReturnURL` | url | Y | | Browser return after store selection |

## 3.3 Store map — browser return fields (p. 15)

| Field | Description |
|---|---|
| `StoreID` | Selected store id |
| `StoreName` | Selected store name |
| `LgsType` | **Chain of the selected store.** Returned as selected; not validated against the request. |

The store map result is posted to `ReturnURL` in the customer's browser only. There is no server notification for store selection; use the Query API (§9) to confirm.

## 7 Pickup with payment — value limit (p. 41)

The collected amount (`Amt`, including freight) must not exceed **NT$20,000**. Requests above the limit are rejected with error code `LGS10012`.

## 10 Parcel status push (p. 52)

| `Status` | Meaning |
|---|---|
| `300` | Arrived at destination store |
| `301` | Collected by customer |
| `302` | Not collected within hold period; returning to sender |
| `303` | Returned to sender |

## 12 Error codes (p. 63)

| Code | Meaning |
|---|---|
| `LGS10012` | Amount exceeds the collection limit for this service |
| `LGS20031` | Store temporarily unavailable; ask the customer to reselect |
| `LGS20040` | Parcel not collected within the hold period; returning to sender |
