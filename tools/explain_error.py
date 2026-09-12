#!/usr/bin/env python3
"""Translate a Taiwan gateway error code into plain words, the likely cause, and the one next action.

Usage:  python tools/explain_error.py MPG02003
        python tools/explain_error.py 10200079 TRA10071 1106
        echo "...response body..." | python tools/explain_error.py -      (scan text for known codes)

Covers the codes a first integration actually meets, from the vendor pages and a shipped shop's
notes; every entry names its source. A code not listed prints the page to look it up on. Add
codes here only with a source; never from memory.
"""
from __future__ import annotations

import re
import sys

# code -> (gateway, plain meaning, likely cause, next action, source)
CODES: dict[str, tuple[str, str, str, str, str]] = {
    # ---- NewebPay MPG / query / refund (NDNF-1.2.5 error tables; lessons from a shipped shop) ----
    "MPG02003": ("NewebPay", "This payment method is not enabled for your shop.",
                 "The console toggle may be on, but NewebPay has not switched the product on at their side (seen: three days with every local check green).",
                 "FIRST flip the toggle in the console (商店資料設定 → 交易手續費及撥款天數 → the method 啟用) and re-probe — an owner enabled 玉山 Wallet and the probe passed within a minute (2026-09-12). If the toggle is already on, this is vendor-side: contact cs@newebpay.com / 02-2786-3655 with your MerchantID and the code, record the date as a wait, and keep building other methods. Re-verify with tools/newebpay/probe_mpg.php, not by placing orders.",
                 "NDNF-1.2.5 MPG error table; mixoweb 2026-08-14..17"),
    "MPG03009": ("NewebPay", "交易資料 SHA 256 檢查不符合 — the signature did not verify.",
                 "HashKey/HashIV do not match this MerchantID on this environment (sandbox keys against core, or the reverse), or TradeSha was computed over the plaintext instead of the TradeInfo ciphertext.",
                 "Run tools/newebpay/probe_mpg.php --selftest (proves the algorithm), then re-copy HashKey (32) and HashIV (16) from 商店資料設定 into .env and confirm NEWEBPAY_ENV matches the keys. Verified live 2026-09-12: a wrong IV returns exactly this code.",
                 "ccore response, 2026-09-12"),
    "MPG00040": ("NewebPay", "The gateway rejected the request shape.", "A required MPG field is missing or malformed (Version, TimeStamp, MerchantOrderNo charset/length, Amt).",
                 "Compare every field against NDNF-1.2.5 §MPG request table; run probe_mpg.php --dry-run and check lengths.", "NDNF-1.2.5"),
    "CHK00007": ("NewebPay", "Signature / decryption check failed.", "TradeSha or TradeInfo does not verify: wrong HashKey/HashIV for this MerchantID, sandbox keys against core, or TradeSha computed over the plaintext instead of the ciphertext.",
                 "Run tools/newebpay/probe_mpg.php --selftest, then re-copy HashKey/HashIV from 商店資料設定 (lengths 32/16) into .env; confirm NEWEBPAY_ENV matches the keys.", "NDNF-1.2.5; mixoweb newebpay.md"),
    "TRA10021": ("NewebPay", "No such transaction.", "You queried an order number NewebPay never saw (a probe id, a typo, or an order that never reached the gateway).",
                 "Fine once. Do not retry in a loop — see TRA10071.", "NDNF-1.2.5 p.95"),
    "TRA10071": ("NewebPay", "Query function LOCKED for 4 hours.", "Too many queries for order numbers NewebPay cannot find within one hour.",
                 "Stop polling. Fix the code that queries unknown orders (bounded, only for orders you actually sent). Wait 4 hours.", "NDNF-1.2.5 p.95; mixoweb §8ad"),
    "TRA10702": ("NewebPay", "Refund function LOCKED for 1 hour.", "Too many 請退款 calls in a short time (a retry loop on refunds).",
                 "Make refunds idempotent (one call per refund, state recorded before the call). Wait 1 hour.", "NDNF-1.2.5; mixoweb §8ad"),
    # ---- NewebPay logistics NDNS-1.0.0 (p.31-32) ----
    "1101": ("NewebPay 物流", "Shipment creation failed.", "Generic create failure.", "Read the Message field; check TradeType, store fields and the value cap.", "NDNS-1.0.0 p.31"),
    "1102": ("NewebPay 物流", "Shop not found.", "UID_/MerchantID wrong, or logistics not enabled for this shop.", "Confirm the shop id and that 物流 is enabled in 會員專區 → 物流中心.", "NDNS-1.0.0 p.31"),
    "1103": ("NewebPay 物流", "Duplicate MerchantOrderNo.", "You created a shipment for this order already.", "Query it (B55) instead of creating again; this is idempotency working.", "NDNS-1.0.0 p.31"),
    "1104": ("NewebPay 物流", "This carrier/service is not enabled for the shop.", "The chain or service variant (取貨付款 vs 不付款) is off at NewebPay.", "Enable it in 物流中心; if the toggle is on, it is vendor-side — dated wait.", "NDNS-1.0.0 p.31"),
    "1105": ("NewebPay 物流", "Store information wrong or blank.", "StoreID/StoreName missing or not a store of that chain.", "Use the store fields exactly as the MPG callback returned them.", "NDNS-1.0.0 p.31"),
    "1106": ("NewebPay 物流", "Your server's IP is not allowed.", "The logistics API only accepts calls from an allowlisted outbound IP; shared or rotating hosting presents an address that is not registered.",
             "Find your host's outbound IP (ask the host whether it is stable). Register it in the NewebPay console (物流 settings). If it rotates: dedicated IP, or move logistics calls to a VPS, or defer 超商取貨. LINE Pay via NewebPay does NOT need this.", "NDNS-1.0.0 p.31; mixoweb §8ab"),
    "1107": ("NewebPay 物流", "Payment order not found.", "createShipment (B52) needs a MerchantOrderNo that already exists as a NewebPay payment order.", "For MPG-paid orders you do not call B52 at all — the payment page created the consignment. Use B53/B55.", "NDNS-1.0.0 p.31; mixoweb newebpay-logistics.md"),
    "1114": ("NewebPay 物流", "Prepaid logistics balance is empty.", "預付費用 not funded, so labels cannot be issued.", "Fund 預付費用 in the console (帳務中心). Put 'prepaid balance' on the readiness card.", "mixoweb DEPLOY.md"),
    "2105": ("NewebPay 物流", "Too many order numbers in one call.", "getShipmentNo (B53) takes at most 10 MerchantOrderNo per call.", "Batch by 10.", "NDNS-1.0.0 p.19"),
    "2106": ("NewebPay 物流", "Too many labels in one print call.", "Per-call label caps differ by chain (7-ELEVEN 18, 全家 8, 萊爾富 18, OK 18).", "Batch per chain within the cap.", "NDNS-1.0.0 p.21"),
    # ---- ECPay AIO (developers.ecpay.com.tw; mixoweb AioCapabilityProbe) ----
    "10200079": ("ECPay", "This payment method is not activated for your merchant (沒有開通此付款方式).", "The method is off in 廠商後台, or ECPay has not activated the product for this MerchantID.",
                 "廠商後台 → 系統開發管理 → 付款方式管理 (or 廠商基本資料 → 付款方式): confirm it is 啟用. Re-run tools/ecpay/probe_aio.php. Still failing → vendor-side; contact ECPay with the MerchantID and code, record the date.", "mixoweb AioCapabilityProbe"),
    "10200073": ("ECPay", "CheckMacValue error.", "HashKey/HashIV do not match this MerchantID on this environment (stage keys against production is the classic), or your CheckMacValue algorithm differs from ECPay's (.NET url-encoding, lowercase, sort).",
                 "Run tools/ecpay/callback.php selftest (known-answer test). Then re-copy HashKey/HashIV from 廠商後台 → 系統開發管理 → 系統介接設定 and confirm ECPAY_ENV matches.", "mixoweb AioCapabilityProbe; p=2902"),
    "10100251": ("ECPay", "MerchantID does not exist here.", "Stage and production MerchantIDs are different; you sent one to the other host.", "Confirm ECPAY_MERCHANT_ID and ECPAY_ENV together.", "mixoweb AioCapabilityProbe"),
    "10300066": ("ECPay", "Payment result still pending — do NOT ship.", "The bank has not confirmed; the notification you got is not a success.",
                 "Treat as unpaid. Query the order (查詢訂單, p=2890) later; only RtnCode=1 is paid.", "p=2878"),
    "10100073": ("ECPay", "CVS / BARCODE payment code issued successfully (取號成功) — this is NOT a payment.", "This arrives on PaymentInfoURL when the customer got a store payment code; money comes later with RtnCode=1.",
                 "Store the code/expiry, show 'waiting for payment', start the expiry clock. Reply 1|OK.", "p=2881"),
    "2": ("ECPay", "ATM virtual account issued (取號成功) — NOT a payment (RtnCode=2 on PaymentInfoURL only).", "Same shape as 10100073 for ATM.",
          "Store the account and ExpireDate, show 'waiting for payment'. Reply 1|OK.", "p=2881"),
}

LOOKUP = {
    "NewebPay": "NDNF-1.2.5 error tables (MPG p.~90, query p.~95) from https://www.newebpay.com/website/Page/content/download_api",
    "NewebPay 物流": "NDNS-1.0.0 p.31-32",
    "ECPay": "https://developers.ecpay.com.tw/?p=2878 (result codes) and the 交易訊息代碼一覽表 linked from it",
}


def explain(code: str) -> str:
    c = code.strip().upper()
    if c in CODES:
        gw, meaning, cause, action, src = CODES[c]
        return f"{c} [{gw}]\n  What it means : {meaning}\n  Likely cause  : {cause}\n  Do this       : {action}\n  Source        : {src}\n"
    fam = "NewebPay" if re.match(r"^(MPG|TRA|CHK)", c) else ("ECPay" if re.match(r"^10\d{6}$", c) else ("NewebPay 物流" if re.match(r"^[124]\d{3}$", c) else "unknown"))
    return f"{c}: not in this table. Look it up: {LOOKUP.get(fam, 'the vendor manual you downloaded (never memory)')}. If you find it, add it here with the source.\n"


def main(argv: list[str]) -> int:
    if not argv:
        print(__doc__); return 1
    if argv == ["-"]:
        text = sys.stdin.read()
        found = sorted({m for m in re.findall(r"\b(?:MPG\d{5}|TRA\d{5}|CHK\d{5}|10\d{6}|1[01]\d{2}|2105|2106)\b", text)})
        if not found:
            print("no known code pattern in the text"); return 1
        argv = found
    for c in argv:
        print(explain(c))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
