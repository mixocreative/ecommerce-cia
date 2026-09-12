# ecommerce-cia — Commerce Integrity Auditor for Taiwan e-commerce

**The only AI coding skill built around how Taiwanese shops actually take money and ship parcels: 藍新 NewebPay, 綠界 ECPay, 超商取貨付款, 電子發票, 個資法 — with live-verified probes, a fool-proof setup guide for first-time builders, and an audit that finds the defects a green test suite cannot.**

[繁體中文 README](README.md) · Works with Claude Code · Codex · Cursor · any agent that reads `SKILL.md`

---

## Why this exists

Every generic "e-commerce audit" prompt assumes Stripe, a US address, a card that settles at authorisation, and a parcel that goes from A to B. A Taiwanese shop is none of that:

- Money arrives **days later** through an ATM 虛擬帳號 or a 超商代碼, and the order must wait without dying.
- **超商取貨付款**: the parcel leaves before the money exists; the store collects cash; the logistics provider settles later; an uncollected parcel returns on a clock nobody set. Four parties hold four different truths about one order.
- The gateway's **hosted page** decides which convenience-store chains the buyer sees — your admin toggle may be a label, not a control.
- LINE Pay through NewebPay is enabled by **a paper form and a phone call**, sandbox included. Nothing in the console turns it on.
- The logistics API refuses calls from an **unregistered outbound IP** (`1106`), which is exactly what shared hosting gives you.
- The manuals are PDFs behind a `403`; the sandbox portal serves a manual **two years older** than production.

This skill encodes all of that as doctrine, checks it with scripts, and explains it in plain words to someone who has never integrated a gateway.

## Three ways to use it

| You are… | Say… | You get… |
|---|---|---|
| **Starting from zero** ("我想用藍新收款，怎麼開始？") | anything about setting up NewebPay / ECPay / 串接 | **Setup mode**: one question at a time with choices, the prerequisite checklist *before* code, a host-capability table for your actual hosting (Bluehost? Hetzner? Vercel?), guided sandbox registration (you type identity and passwords, never the AI), every method **proved on** by a probe, a readiness card with dated waits |
| **Have a shop, about to launch** | `pre-launch audit, Screen tier` | **Audit mode**: a Viable-System-Model map of your codebase, 22 sweeps for cross-boundary defects (dead controls, TOCTOU, fail-open callbacks, blind watchdogs, unrendered states), the four-corner walk (customer × admin × logistics × gateway), Taiwan + global compliance layers, a report that opens with five plain lines an owner can act on |
| **Want the universal code audit too** | `run /cia and /ecommerce-cia together` | **Paired mode**: one discovery, one map, one line per sweep, no duplicate findings — the sibling [`cia`](../cia) skill folds in |

## 60-second start

```bash
# Claude Code
git clone https://github.com/<you>/ecommerce-cia ~/.claude/skills/ecommerce-cia
# Codex
git clone https://github.com/<you>/ecommerce-cia ~/.codex/skills/ecommerce-cia
# then, in any shop directory:
#   "我想用藍新金流收款，怎麼開始？"      -> setup mode
#   "pre-launch audit, Screen tier"       -> audit mode
```

Requirements: Python 3.10+ (stdlib only) and PHP 8 for the gateway probes. No third-party packages.

## Live-verified, not assumed

Everything below was run against real endpoints on 2026-09-12 and is logged in [`tests/RUNS.md`](tests/RUNS.md):

| Check | Result |
|---|---|
| `tools/newebpay/probe_mpg.php` on a real NewebPay sandbox shop | CREDIT · WEBATM · VACC · CVS · BARCODE · LINEPAY · ESUNWALLET → **PASS** (server-side `payType` confirms); a product not enabled → `MPG02003`; a wrong HashIV → `MPG03009` |
| `tools/ecpay/probe_aio.php` on ECPay's public stage merchant | Credit, BNPL → **PASS**; wrong keys → `10200073` |
| `tools/ecpay/callback.php selftest` | reproduces ECPay's published `CheckMacValue` worked example byte-for-byte |
| `tools/newebpay/fetch_manuals.py` | reads the production download page (403 to `curl`) and exposes **65 documents** the visible tab hides — including the application forms behind every "why is this method still off" |
| Cold runs by a fresh agent | setup Q1 · setup 4-turn · plain-language audit · paired — **0 false positives**, 16/16 defects on the fixture shop |

## What is inside

```
SKILL.md                         the runbook: routing, discovery, 7-step protocol, autonomy contract,
                                 sweep index, escalation, setup mode, plain-language contract, start menu
references/
  sweeps.md                      S1–S22, the cross-boundary sweeps, with report-line formats
  taiwan-adapter.md              TW-0…TW-14: CVS payment vs CVS logistics, 取貨付款 money states,
                                 統一發票, 消保法, vendor document locations
  newebpay-onboarding.md         藍新 from zero: manuals, choice menu, prerequisites, host table,
                                 sandbox registration, console activation + probes, wiring, go-live, gotchas
  ecpay-onboarding.md            綠界 from zero: markdown-twin docs, public stage keys, CheckMacValue,
                                 1|OK, SimulatePaid, DoAction production-only, two logistics families
  jurisdictions.md               EU · Japan · US · UK at the same depth
  global-compliance.md           terms & privacy across 13 regimes (GDPR, 個資法, PIPA, APPI, LGPD…)
  doctrine.md / domains.md / theory.md / reporting.md
tools/
  newebpay/  detect · fetch_manuals · probe_mpg · callback (verify|make) · readiness
  ecpay/     detect · fetch_docs · probe_aio · callback (verify|make|sign|selftest)
  explain_error.py               MPG02003? 10200079? 1106? → meaning, cause, the one next action
tests/
  fixture-shop/                  a PHP shop with 16 known defects + an answer key
  RUNBOOK.md · RUNS.md           how to score a run; the ledger of every run so far
```

## How it differs from what already exists

| | Generic audit prompts | Vendor API skills (e.g. ECPay's official `ecpay-api-skill`, `paid-tw/skills`) | **ecommerce-cia** |
|---|---|---|---|
| Knows 取貨付款 has two facts (goods vs money) | no | no | **yes — TW-7, S15, S16** |
| Tells you what to obtain *before* coding, and who must act | no | no | **yes — readiness card** |
| Checks whether your **host** can do what the gateway needs | no | no | **yes — S19 per hosting shape** |
| Proves a method is enabled instead of trusting a toggle | no | no | **yes — live probes** |
| Generates API code | some | **yes, deeply** | defers to the vendor skill where one exists |
| Finds the defect under a green test suite | no | no | **yes — 22 sweeps, four-corner walk** |
| Speaks to a non-engineer | no | no | **yes — plain-language contract** |

Use the vendor skill for the API calls. Use this one for everything around them.

## Roadmap

- PAYUNi 統一金流 and TapPay onboarding guides (in progress)
- Japan and EU adapters at Taiwan depth (jurisdictions exist; provider guides do not yet)
- A Codex-runtime cold run to mirror the Claude ones

## Credits and provenance

The doctrine grew out of shipping a real Taiwanese shop (NewebPay + ECPay, 超商取貨付款, hand-written 統一發票) and writing down every lesson the manuals did not contain. Every number in the guides is marked *verify-current*; every rule that came from a real defect is marked *(lesson)*. The sibling skill [`cia`](../cia) carries the universal, non-commerce half of the same method.

License: MIT.
