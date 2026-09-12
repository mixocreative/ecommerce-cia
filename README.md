# ecommerce-cia — 台灣電商金流串接與完整性審查 Skill

[![tests](https://github.com/mixocreative/ecommerce-cia/actions/workflows/tests.yml/badge.svg)](https://github.com/mixocreative/ecommerce-cia/actions/workflows/tests.yml) [![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE) [![GitHub stars](https://img.shields.io/github/stars/mixocreative/ecommerce-cia?style=social)](https://github.com/mixocreative/ecommerce-cia/stargazers)

**唯一專為台灣電商實務量身打造的 AI 程式碼檢測與串接 Skill：藍新 NewebPay、綠界 ECPay、統一金流 PAYUNi、TapPay、超商取貨付款、電子發票、個資法 —— 搭配實機驗證探針、新手也能一次搞定的串接引導，以及能在綠燈測試背後抓出潛藏漏洞的審查機制。**

[English README](README.en.md) · 支援 Claude Code · Codex · Cursor · 以及任何能讀取 `SKILL.md` 的 Agent

---

## 為什麼需要這個 Skill？

一般常見的「電商審查」Prompt 往往假設你用的是 Stripe、美國地址、授權即請款的信用卡，以及單純點對點的包裹物流。但台灣電商完全不是這麼一回事：

- 款項透過 ATM 虛擬帳號或超商代碼在**數天後**才進來，訂單必須在不失效的前提下持續等待。
- **超商取貨付款**：貨還沒收到錢就先寄出；超商門市代收現金；物流商之後才撥款；沒人領的包裹會照著一個沒人設定過的時限退回。四個角色對同一筆訂單各自掌握不同的真實狀態。
- 金流頁面的**託管頁面**決定了買家能看到哪些超商通路 —— 你後台的開關可能只是個標籤，而不是真正的控制項。
- 透過藍新啟用 LINE Pay 需要**紙本表單與電話聯繫**，連測試環境也是如此。管理後台裡沒有任何按鈕可以直接開啟它。
- 物流 API 會直接拒絕來自**未註冊對外 IP**（`1106`）的呼叫，而這恰好就是共享主機（Shared Hosting）會給你的環境。
- 文件手冊是藏在 `403` 阻擋背後的 PDF 檔；測試環境入口提供的說明書比正式環境**舊了整整兩年**。

本 Skill 將這些實務經驗提煉為規範準則，透過自動化腳本進行檢測，並用連沒串過金流的新手都能聽懂的大白話清晰解釋。

## 三種使用方式

| 你的需求是… | 請說… | 你會獲得… |
|---|---|---|
| **從零開始**（「我想用藍新收款，怎麼開始？」） | 任何關於設定 NewebPay / ECPay / 串接 的需求 | **引導模式（Setup mode）**：每次只問一個帶選項的問題、寫程式碼*之前*的前置準備清單、針對你實際主機環境的主機相容性表格（Bluehost？Hetzner？Vercel？）、測試環境註冊引導（身分資料與密碼由你親自輸入，AI 不代打）、每種支付方式均經由探針**實測證明**已開啟、一張把每個「等別人」項目都標上日期與負責人的準備就緒卡片 |
| **已有現成電商，準備上線** | `pre-launch audit, Screen tier` | **審查模式（Audit mode）**：針對你程式碼庫進行 Viable-System-Model 架構解析、22 項跨邊界缺陷掃描（失效控制項、TOCTOU、Fail-Open Callback、盲目 Watchdog、未渲染狀態）、四角演練（顧客 × 後台管理者 × 物流 × 金流）、台灣 + 全球合規防護層，以及一份以五行白話文開頭、讓老闆能立即採取行動的報告 |
| **同時想要通用型程式碼審查** | `run /cia and /ecommerce-cia together` | **雙向配對模式（Paired mode）**：專案偵測只做一次、架構地圖只畫一張、每項掃描只出一行，同一個問題不會回報兩次 —— 完美整合兄弟專案 [`cia`](../cia) skill |

## 60 秒快速開始

```bash
# Claude Code
git clone https://github.com/mixocreative/ecommerce-cia ~/.claude/skills/ecommerce-cia
# Codex
git clone https://github.com/mixocreative/ecommerce-cia ~/.codex/skills/ecommerce-cia
# 接著在任何電商專案目錄下輸入：
#   "我想用藍新金流收款，怎麼開始？"      -> 引導模式 (setup mode)
#   "pre-launch audit, Screen tier"       -> 審查模式 (audit mode)
```

系統需求：Python 3.10+（僅需標準函式庫）與 PHP 8（用於執行金流探針）。不需安裝任何第三方套件。

## 實機驗證，絕非憑空臆測

以下所有項目皆於 2026-09-12 在真實 API 端點上執行驗證完成，並記錄於 [`tests/RUNS.md`](tests/RUNS.md)：

| 測試項目 | 測試結果 |
|---|---|
| 在真實 NewebPay 測試店家執行 `tools/newebpay/probe_mpg.php` | CREDIT · WEBATM · VACC · CVS · BARCODE · LINEPAY · ESUNWALLET → **PASS**（經伺服器端 `payType` 確認）；未啟用的支付方式 → `MPG02003`；錯誤的 HashIV → `MPG03009` |
| 在 ECPay 公開測試店家執行 `tools/ecpay/probe_aio.php` | Credit, BNPL → **PASS**；金鑰錯誤 → `10200073` |
| 執行 `tools/ecpay/callback.php selftest` | 逐 Byte 完全重現 ECPay 官方範例的 `CheckMacValue` 算碼結果 |
| 對 PAYUNi 測試區執行 `tools/payuni/probe_upp.php` | 拒絕路徑精確（`JS_INFO.success=false` 商店不存在）；AES-256-GCM 封裝通過自我測試 |
| 執行 `tools/newebpay/fetch_manuals.py` | 成功讀取正式環境下載頁面（用 `curl` 會被擋 `403`），抓出一般頁籤隱藏的 **65 份文件** —— 包含解答「為什麼這個支付方式一直開不起來」的所有申請表單 |
| 由全新 Agent 進行無快取冷啟動（Cold run） | setup Q1 · setup 4-turn · 易懂白話審查 · paired 模式 —— **0 誤報（False positive）**，準確抓出測試電商中 16/16 個已知漏洞 |

## 包含哪些內容

```
SKILL.md                         執行手冊：路由、專案偵測、7 步協定、自主權合約、
                                 掃描索引、升級機制、引導模式、白話文合約、啟動選單
references/
  sweeps.md                      S1–S22，跨邊界掃描規則，包含報告輸出格式
  taiwan-adapter.md              TW-0…TW-14：超商付款 vs 超商取貨、取貨付款金額狀態、
                                 統一發票、消保法、廠商文件位置
  newebpay-onboarding.md         藍新從零開始：文件手冊、選擇選單、前置條件、主機支援表、
                                 測試環境註冊、後台啟用 + 探針實測、串接程式碼、上線流程、常見坑點
  ecpay-onboarding.md            綠界從零開始：Markdown 雙生文件、公開測試金鑰、CheckMacValue、
                                 1|OK、SimulatePaid、DoAction 僅限正式環境、兩大物流體系
  payuni-onboarding.md           統一金流從零開始：AES-256-GCM 加密封裝、UPP 旗標與金額上限、
                                 同一頁整合 7-ELEVEN 物流、模擬繳費、LINE Pay 測試區任意 Channel 即可用
  tappay-onboarding.md           TapPay：前端 Token 化 SDK、Pay by Prime、各式錢包、3DS 通知、無超商
  jurisdictions.md               歐盟 · 日本 · 美國 · 英國 同等深度說明
  global-compliance.md           跨 13 種法規體系的條款與隱私權（GDPR、個資法、PIPA、APPI、LGPD…）
  doctrine.md / domains.md / theory.md / reporting.md
tools/
  newebpay/  detect · fetch_manuals · probe_mpg · callback (verify|make) · readiness
  ecpay/     detect · fetch_docs · probe_aio · callback (verify|make|sign|selftest)
  payuni/    detect · fetch_docs（ShowDoc API）· crypto（GCM selftest|encrypt|decrypt）· probe_upp
  tappay/    probe_prime（dry-run、--prime、--query）
  explain_error.py               MPG02003? 10200079? 1106? → 顯示含義、原因與唯一下一步行動
tests/
  fixture-shop/                  包含 16 個已知缺陷與標準解答的 PHP 測試電商
  RUNBOOK.md · RUNS.md           如何評分執行過程；至今每一次執行的完整紀錄
```

## 與現有工具的差異

| | 一般通用型審查 Prompt | 廠商 API Skill（例如綠界官方 `ecpay-api-skill`、`paid-tw/skills`） | **ecommerce-cia** |
|---|---|---|---|
| 理解取貨付款包含兩種獨立事實（貨物 vs 金額） | 否 | 否 | **是 — TW-7, S15, S16** |
| 在寫程式碼*之前*提示所需準備事項與負責窗口 | 否 | 否 | **是 — 準備就緒卡片** |
| 檢查你的**主機環境**是否滿足金流商需求 | 否 | 否 | **是 — S19 依據主機類型分析** |
| 透過探針實測驗證支付方式是否開啟，而非盲信後台開關 | 否 | 否 | **是 — 實機探針驗證** |
| 自動生成 API 串接程式碼 | 部分支援 | **是，極為深入** | 若有官方 Skill 則優先委派 |
| 在全綠燈的測試套件下依然抓出漏洞缺陷 | 否 | 否 | **是 — 22 項掃描、四角演練** |
| 能以非技術人員聽得懂的語言對話 | 否 | 否 | **是 — 白話文對話機制** |

API 呼叫交給廠商的專用 Skill。這套 Skill 則負責幫你把關周遭的所有細節與防護機制。

## 開發路線圖

- 申請一個 PAYUNi 測試店家，驗證 PASS 路徑（拒絕路徑已驗證）
- 比照台灣深度打造日本與歐盟轉接層（法規層已有，金流商引導尚未撰寫）
- 執行 Codex 運行環境的無快取測試（Cold run），以比照 Claude 測試結果

## 致謝與專案由來

本 Skill 的核心準則來自於實際上線經營台灣電商網站（整合藍新 NewebPay + 綠界 ECPay、超商取貨付款、手寫統一發票；PAYUNi 與 TapPay 則依官方文件撰寫）的經驗，並記錄下官方技術手冊中未提及的所有坑點。指南中的每個數據均標註 *verify-current*（驗證最新）；源自真實漏洞的每條規則皆標註 *(lesson)*（實戰教訓）。兄弟專案 [`cia`](../cia) 則繼承了本方法論中通用、非電商部分的審查能力。

授權條款：MIT。