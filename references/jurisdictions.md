# §23 Global Provider / Jurisdiction Adapter Rule

Loaded by `ecommerce-cia` for any non-Taiwan selling jurisdiction the audit profile (§3) names. Taiwan has its own adapter: `taiwan-adapter.md`.

# 23. Global Provider / Jurisdiction Adapter Rule

Taiwan is one adapter.

The architecture must allow equivalent adapters for other regions.

Examples:

## United States

Potential concerns:

- sales tax
- card/payment processors
- ACH
- state-specific requirements

## European Union

Potential concerns:

- VAT
- GDPR
- payment regulation
- consumer withdrawal rules

## Japan

Potential concerns:

- Japanese addresses
- consumption tax
- convenience-store payment
- local payment providers

## United Kingdom

Potential concerns:

- VAT
- consumer rights
- UK-specific payment/tax requirements

The auditor must derive behavior from:

`GLOBAL INVARIANTS`

+

`JURISDICTION RULES`

+

`PROVIDER CAPABILITIES`

+

`MERCHANT POLICY`

Never assume one country's checkout model is universal.

