#!/usr/bin/env python3
"""Find mainland-Chinese usage in a skill that is written for Taiwanese readers.

    python tools/zh_check.py           # report every hit with its line and context
    python tools/zh_check.py --gate    # exit 1 if any hit is not on the allowlist
    python tools/zh_check.py --tone    # also flag translationese patterns (advisory, never gated)

Why this is a tool and not a habit: on 2026-09-24 a blanket `代碼 -> 程式碼` sweep turned
**超商代碼** into 超商程式碼 in eight places - 超商代碼 is the standard Taiwanese term for a
convenience-store payment code, in the README of a skill built for that market. A rename applied
by pattern rather than by meaning takes every site that merely matches the pattern, which is the
S9 defect this skill grades in other people's code.

So this reports; it never rewrites. Each hit prints its line so a human decides, and the terms
that are correct in a Taiwanese commerce context are allowlisted with the reason.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# mainland form -> (Taiwanese form, note). Only terms that genuinely differ in technical writing.
TERMS: dict[str, tuple[str, str]] = {
    "軟件": ("軟體", ""),
    "硬件": ("硬體", ""),
    "網絡": ("網路", ""),
    "信息": ("資訊", ""),
    "數據庫": ("資料庫", ""),
    "調用": ("呼叫", ""),
    "默認": ("預設", ""),
    "內存": ("記憶體", ""),
    "緩存": ("快取", ""),
    "服務器": ("伺服器", ""),
    "進程": ("行程", ""),
    "線程": ("執行緒", ""),
    "接口": ("介面", ""),
    "字符": ("字元", ""),
    "運行": ("執行", ""),
    "質量": ("品質", ""),
    "密鑰": ("金鑰", ""),
    "演示": ("展示", ""),
    "硬核": ("硬派", ""),
    "用戶": ("使用者", ""),
    "訪問": ("存取", ""),
    "屏幕": ("螢幕", ""),
    "打印": ("列印", ""),
    "磁盤": ("磁碟", ""),
    "視頻": ("影片", ""),
    "音頻": ("音訊", ""),
    "插件": ("外掛", ""),
    "兼容": ("相容", ""),
    "集成": ("整合", ""),
    "智能": ("智慧", ""),
    "交互": ("互動", ""),
    "對象": ("物件", ""),
    "函數": ("函式", ""),
    "變量": ("變數", ""),
    "數組": ("陣列", ""),
    "指針": ("指標", ""),
    "隊列": ("佇列", ""),
    "遞歸": ("遞迴", ""),
    "帶寬": ("頻寬", ""),
    "端口": ("連接埠", ""),
    "證書": ("憑證", ""),
    "令牌": ("權杖", ""),
    "會話": ("工作階段", ""),
    "冗余": ("備援", ""),
    "登錄": ("登入", ""),
    "賬號": ("帳號", ""),
    "賬戶": ("帳戶", ""),
    "余額": ("餘額", ""),
    "並發": ("並行", ""),
    "灰度": ("灰階", ""),
    # context-dependent: reported, never auto-anything
    "代碼": ("程式碼", "ONLY when it means source code - 超商代碼/拒絕代碼/錯誤代碼 are correct"),
    "落地": ("轉化／實作", "'理論落地' is mainland; 落地 in a logistics sense can be fine"),
    "響應": ("回應", "'響應式' for responsive layout is acceptable in TW"),
}

# Correct in Taiwanese technical and commerce writing. The reason is part of the entry, because
# an allowlist with no reasons becomes a place to hide things.
ALLOW: dict[str, str] = {
    "超商代碼": "the standard TW term for a convenience-store payment code",
    "拒絕代碼": "a numeric refusal code, not source code",
    "錯誤代碼": "a numeric error code",
    "四位數代碼": "a numeric code",
    "代碼一覽表": "vendor's own table name (ECPay 交易訊息代碼一覽表)",
    "響應式": "responsive (layout); standard in TW front-end writing",
    "不變量": "invariant - the standard TW term; 變量 here is a substring, not a variable",
    "受控對象": "cybernetics: the entity under control (Ashby). OOP 對象 -> 物件 still applies",
    "控制對象": "same as 受控對象",
    "標示對象": "對象 = the party concerned (適用對象/交往對象); standard TW, not OOP",
    "適用對象": "same",
    "貨態代碼": "ECPay's own console menu name (物流貨態代碼查詢)",
}

# Translationese: phrasing that is grammatical, uses no mainland vocabulary, and still reads as
# translated English. These are patterns rather than words, so each one is a PROMPT to re-read
# the line, not a verdict - the tool prints the line and a human decides.
TONE: dict[str, str] = {
    "進行了": "「進行+動詞」多半是英文 -ing 的直譯；台灣寫法通常直接用那個動詞",
    "進行一個": "同上，且「一個」多半是 a/an 的直譯",
    "被認為是": "英文被動語態直譯；中文少用「被」，改主動",
    "被稱為": "同上；可用「稱為」或直接敘述",
    "的的": "「的」連續，幾乎都是修飾語過長",
    "透過使用": "冗詞；「透過」或「用」擇一",
    "藉由使用": "同上",
    "的事實": "the fact that 的直譯",
    "在...的情況下": "in the case of 的直譯",
    "不僅僅": "not only 的直譯；台灣多用「不只」",
    "在某種程度上": "to some extent 的直譯",
    "眾所周知": "翻譯腔套語",
}

SKIP_DIRS = {".git", "node_modules", "vendor", "__pycache__", "var", "build", "dist"}
SKIP_SUFFIX = {".sqlite", ".png", ".gif", ".jpg", ".lock", ".pyc"}
HAN = re.compile(r"[一-鿿]")


def scan() -> list[tuple[Path, int, str, str, str, str]]:
    hits = []
    for path in sorted(ROOT.rglob("*")):
        if not path.is_file() or path.suffix.lower() in SKIP_SUFFIX:
            continue
        if any(part in SKIP_DIRS for part in path.parts):
            continue
        # These discuss the terms on purpose: the checker's own table, the hook that runs it,
        # and the memory note explaining why a blanket replace is forbidden.
        if path.name in {"zh_check.py", "pre-push"}:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        if not HAN.search(text):
            continue

        for lineno, line in enumerate(text.splitlines(), 1):
            if "--tone" in sys.argv:
                for pattern, why in TONE.items():
                    if pattern in line:
                        hits.append((path, lineno, pattern, "(re-read this line)", why, line.strip()))
            for bad, (good, note) in TERMS.items():
                idx = 0
                while (idx := line.find(bad, idx)) != -1:
                    window = line[max(0, idx - 6):idx + len(bad) + 6]
                    allowed = next((phrase for phrase in ALLOW if phrase in window), None)
                    if allowed is None:
                        hits.append((path, lineno, bad, good, note, line.strip()))
                    idx += len(bad)
    return hits


def main() -> int:
    hits = scan()
    if not hits:
        print(f"zh: clean - no mainland usage found under {ROOT.name}/")
        return 0

    print(f"zh: {len(hits)} hit(s) under {ROOT.name}/ - read each line before changing it\n")
    for path, lineno, bad, good, note, line in hits:
        rel = path.relative_to(ROOT)
        print(f"  {rel}:{lineno}")
        print(f"    {bad} -> {good}" + (f"   [{note}]" if note else ""))
        print(f"    {line[:150]}")
        print()

    print("Never fix these with a blanket replace: 超商代碼 became 超商程式碼 that way, in the")
    print("README of a skill built for the Taiwanese market. Decide per line.")

    # --tone is advisory and never gates: every pattern in TONE has a legitimate use, and a
    # gate on judgement would be a gate that gets switched off.
    if "--gate" in sys.argv:
        vocab = [h for h in hits if h[2] not in TONE]
        return 1 if vocab else 0
    return 0


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(main())
