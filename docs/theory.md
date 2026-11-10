# ecommerce-cia — the theory

> Moved from the README on 2026-11-10, text unchanged, so the README stays a front door. [Back to the README](../README.md).

## The theory｜底層理論

Beer's Viable System Model (*Brain of the Firm*, 1972; *The Heart of Enterprise*, 1979) states that anything which stays alive in a changing environment has the same five-part structure, repeated at every level of recursion:

> Stafford Beer 所提出的可存活系統模型（Viable System Model, VSM；參見《Brain of the Firm》1972、《The Heart of Enterprise》1979）核心概念在於：任何能夠在動態環境中持續存活的系統，必然具備由五個子系統構成的結構，而且這種結構在每一個遞迴層級上都完美複製：

| System｜系統 | Role｜扮演角色 | In a shop｜對應到電商系統的具體模組 |
|---|---|---|
| **1** | does the work｜執行層（Operations） | checkout, order placement, payment capture, fulfilment, entitlement grant｜處理結帳、建立訂單、發起請款、安排出貨、發放數位商品下載權限 |
| **2** | damps oscillation between the parts of System 1｜協調層（Coordination） | stock reservation, payment deadlines, callback idempotency, order state machines｜防止 System 1 各模組互相打架：包含庫存保留鎖定、付款時效控制、Callback 冪等性處理、訂單狀態機 |
| **3** | commands and allocates resources to System 1｜管理層（Control） | payment-method toggles, shipping rules, tax settings, admin pages, feature flags｜發布指令與分配資源給 System 1：包含付款方式開關、運費算表、稅務設定、Admin 後台介面、Feature Flag 控制 |
| **3\*** | audits System 1 directly, bypassing its own reports｜獨立稽核（Audit） | test suites, reconciliation against provider statements, probes, sandbox walks｜不聽信 System 1 的自我報告，直接進行實地查帳：包含 Test Suite、金流對帳腳本、探測 Monitoring Script、Sandbox 實測 |
| **4** | faces the environment and the future｜研發與外觀（Intelligence） | gateway specs, logistics APIs, callback formats, tax and invoice regulation｜掌握外部環境變化與未來規格：包含金流商 API 規格書、物流 API、Webhook 格式、稅務與電子發票法規 |
| **5** | identity and policy; receives the algedonic (pain) signal｜政策與願景（Policy） | fail-closed defaults, refund policy, kill switches, amount-mismatch alerts｜定義系統身分與核心政策，並接收全局「痛覺」訊號：包含故障時預設關閉（Fail-Closed）、退款政策、緊急熔斷機制、金額不符警報 |

The systems are joined by **channels**. Ashby's Law of Requisite Variety says a channel must carry as much variety as the thing it regulates, otherwise the control it claims to exercise is fictional. Beer's diagnosis of a failing organisation is almost never "a department is incompetent"; it is "a channel is missing, saturated, or bypassed".

> 系統與系統之間完全仰賴**通道**（Channel）傳遞訊息。Ashby 的必要多樣性定律（Law of Requisite Variety）指出：一條通道能夠承受的變化量，必須等同於它所要控制標的之變化量，否則所謂的「控制」只不過是自我安慰。Beer 在診斷出問題的組織時，結論幾乎從來不是「某個部門能力太差」，而是「某條訊息通道斷了、塞住了，或是被偷跑繞過了」。

A shop fails the same way. It was built after a production shop passed static analysis, linting and a green unit suite while carrying these broken channels in its payment path:

> 電商系統出包的規律完全一模一樣。這個 Skill 的開發起點，源自一個已經上線運作的電商專案：明明 phpstan 全過、phpcs 全過、Unit Test 一片綠燈，但核心付款路徑上的通道卻早已斷得一塌糊塗：

- **System 1 → System 1 across time, no System 2.** An expiry worker selected overdue orders, then cancelled by status only. A bank-transfer callback that extended the deadline between the two steps was ignored; stock was returned on a live order.
  > **System 1 → System 1 進行跨時間操作，中間卻缺少了 System 2 的協調。** 負責處理逾期取消的 Cron Job，先用 SELECT 挑出過期的訂單，再單純依據狀態跑 UPDATE 取消。如果在兩步執行的時間差內，ATM 的 Callback 剛好進來並延長了付款期限，這個變更會被 Cron Job 完全無視，結果就是一張還在付款期限內的活訂單，庫存直接被系統硬生生退掉。
- **System 3 → System 1 read at two different times.** The reservation deadline was frozen at placement from settings, while the payment page re-read the enabled methods on every visit. Enabling a days-long ATM method after placement offered it against a thirty-minute hold.
  > **System 3 → System 1 的設定值在兩個不同的時間點被重複讀取。** 庫存保留時間在客人下單的那一刻就已經凍結寫死，但付款頁面卻每次都重新讀取後台「當前開啟的付款方式」。如果下單後管理員才在後台開啟需要耗時數天的 ATM 轉帳，客人就會看到這個選項，但庫存保留期其實只有當初那 30 分鐘。
- **System 4 ↔ vendor, semantic drift.** The gateway self-heal parser read the card-only `PaymentMethod` field. The vendor spec defines a shared `PaymentType` for every family; non-card rejections were invisible.
  > **System 4 ↔ 金流商之間產生了語意漂移（Semantic Drift）。** 金流模組內建的錯誤自我修復 Parser，拿去解析的欄位居然是信用卡專屬的 `PaymentMethod`；但金流商規格書明明寫得清清楚楚，所有付款方式共用的通用欄位叫做 `PaymentType`。這導致所有非信用卡交易的失敗訊息全被系統當成空氣。
- **System 3 → System 1 channel absent.** Admin per-method toggles existed and nothing in checkout read them. A comment promised a follow-up commit that never landed.
  > **System 3 → System 1 的控制通道根本不存在。** 後台明明做好了各種付款方式的開關介面，但前端結帳流程卻沒有半行程式碼去讀取這個設定。Code 裡面只留了一行「下個 commit 再補」的註解，而那個 commit 永遠沒有出現過。
- **System 5 default missing.** A configuration read failure defaulted to "offer card anyway".
  > **System 5 的預設安全機制（Fallback）徹底失聯。** 當系統抓不到設定檔時，預設的處置邏輯居然是「不管了，先讓客人刷卡再說」。

A second auditor found all of them by tracing channels, not by reading functions. This skill makes that the default.

> 當初第二位 Auditor 完全不是靠「逐個 Function 讀 Code」，而是靠「順著溝通通道一路把脈」才把這些隱藏 Bug 抓出來的。這個 Skill，就是把這套稽核手法直接自動化。

## The stance this skill takes from Beer｜傳承自 Beer 模型的核心心法

- **The purpose of a system is what it does** (POSIWID). Not what the docs, the comments or the admin screen say it does. An audit reads behaviour, and treats the written intent as a hypothesis to test against the running system.
  > **系統真正的目的，看它實際產出的行為就知道**（POSIWID）。不要去相信文件、註解或後台畫面寫了什麼。稽核只相信系統的真實行為；寫在紙上的意圖，充其量只是待證實的假設。
- **Recursion.** Every System 1 unit is itself a viable system with its own 1–5. A payment module, a fulfilment pipeline, an entitlement service each has its own control, its own audit, its own policy; the audit descends one level and asks the same five questions again.
  > **遞迴結構（Recursion）。** 每個 System 1 模組拉近來看，本身都是一個獨立運作的可存活系統，內部同樣具備 1–5 的結構。金流模組、物流出貨、數位權限發放各自擁有獨立的控制、稽核與政策機制；稽核往下剖析一層，就是把同樣這五個問題再問一遍。
- **Variety engineering.** Complexity is not removed, it is absorbed or amplified. Every guard, validator, idempotency key and state machine is a variety attenuator; every default and fallback is an amplifier of whatever the environment throws in. Ask of each: does it match the variety of what it faces?
  > **多樣性工程（Variety Engineering）。** 系統的複雜度不可能憑空消失，只會被消化吸收或是被無腦放大。每一個 Guard 條件、驗證器、冪等鍵（Idempotency Key）、狀態機，都在幫系統削減不確定性；而每一個隨便寫的預設值和 Fallback，都在把外界傳進來的混亂放大。面對每個機制都要拷問：它真的扛得住外面的變化量嗎？
- **Autonomy with cohesion.** System 1 must be free to act without asking System 3 on every step (a checkout that blocks on live config on every request is not autonomous), yet System 3 must still be able to command it (a toggle nothing reads is not cohesion). Both failures are channel failures.
  > **保持自主，但必須維持一致性。** System 1 必須具備獨立作業的能力，不用每動一步都要向 System 3 請示（每次 Request 都得即時敲 API 拿設定的結帳流程絕非良策）；但 System 3 也必須具備絕對的控制力（如果後台改了設定卻沒半行 Code 去讀，那就是失控）。這兩種極端都是通道故障的警訊。
- **The auditor is System 3\*.** This skill is the channel that bypasses the system's own reports. A green suite is System 3's report about itself; the audit exists precisely because that report can be vacuous.
  > **Auditor 的定位就是 System 3\*。** 這個 Skill 的存在，就是為了建立一條能夠繞過系統「自我感覺良好報告」的獨立通道。測試全綠只是 System 3 在自我安慰；稽核之所以必要，是因為這份綠燈報告很可能根本是空的。
- **Algedonic signals must reach System 5.** A pain signal that stops in a log file has not reached policy. Every alert, every catch block, every refund path is traced to the point where identity decides.
  > **痛覺訊號必須一路傳遞到 System 5。** 如果系統出錯的痛覺訊號最後只被默默關在 Log 檔裡，代表它根本沒傳到政策層。每一個 Alert 告警、每一個 Catch 區塊、每一條退款流程，都要一路追查到「到底由誰來做最終決策」。

## How the theory becomes procedure｜如何將理論轉化為實作流程

1. **Map the shop onto Systems 1–5 first** (§0.9 step 0) and report the table: every component, its primary system, its channels as `producer → consumer`.
2. **Walk the channels** with twenty-two mandatory sweeps (§0.9); each defect class below is a named kind of broken channel, and each sweep enumerates its sites from the map rather than from grep.
3. **Grade viability, not just correctness**: §2 asks whether each of the five systems exists for money, stock, orders and entitlements, whether System 3\* is independent of System 3, whether an algedonic path (amount mismatch, callback auth failure, self-heal) reaches System 5.
4. **Report structurally**: every finding names its defect class and the VSM channel it sits on.

> 1. **第一步先把電商模組對應到 System 1–5 架構**（詳見 §0.9 第 0 步），並產出一張完整的對照表：標註每個元件、所屬的子系統，以及彼此間的資料通道（`producer → consumer`）。
> 2. **順著通道逐一體檢**：強制執行二十二項深度掃描（詳見 §0.9）。後面列出的每種缺陷類型，本質上都是某條出了問題的斷鏈通道；每個掃描點都是直接對照架構圖來查，絕對不是拿 `grep` 隨便搜搜字串而已。
> 3. **評判標準是「能不能在真實世界存活」，而不只是「語法對不對」**：§2 會嚴格抽查金流、庫存、訂單、數位權限這四大區塊各自的五層系統是否齊備、System 3\* 稽核機制有沒有獨立於 System 3 之外，以及各類痛覺路徑（如金額不符、Callback 驗簽失敗、自我修復機制）有沒有順暢通到 System 5。
> 4. **輸出結構化報告**：針對抓到的每一個問題，精確標明缺陷類型以及所屬的 VSM 溝通通道。

## The defect classes it hunts｜它專門獵捕的缺陷類型：跨邊界不變量違反

These are **cross-boundary invariant violations**: integration-level, emergent defects where every function is correct and the bug lives between them. Each sweep in section 0.9 names one; every finding states its defect class and its boundary location as `producer → consumer`:

> 這些問題全屬於**跨邊界不變量違反（Cross-Boundary Invariant Violation）**：單看每個 Function 都寫得很完美，但 Bug 偏偏就出在 Function 與 Function 交接的縫隙裡。§0.9 中的每個掃描項都對應一種缺陷；每個查出的缺陷都會明確列出缺陷名稱與發生邊界（`producer → consumer`）：

| Term｜專業術語 | Meaning｜實際代表的意思 |
|---|---|
| **TOCTOU race**｜TOCTOU 競態條件 | a predicate checked at one step, dropped at the step that acts｜某個狀態在 SELECT 時明明確認過沒問題，結果到了 UPDATE 那一刻條件卻早就變了 |
| **Temporal coupling / stale snapshot**｜時間耦合／過期快照 | a value frozen at one moment, re-read live by a later reader｜某個數值在下單時就被凍結起來，但後續的邏輯卻又跑去讀取最新的即時變數 |
| **Semantic drift**｜語意漂移（Semantic Drift） | code's reading of an external field diverges from the vendor spec｜程式碼對外部 API 欄位涵義的理解，跟金流商原廠 Spec 寫的完全對不上 |
| **Dead control**｜死開關（Dead Control） | an admin toggle or flag no runtime path consumes｜後台明明做好了開關 UI，但全域程式碼中沒有任何一條執行路徑真正去讀取它 |
| **Fail-open default**｜出錯就放行（Fail-Open） | an error path that proceeds as if the read succeeded｜當系統跑到 Error Handling 路徑時，居然把它當成成功回應繼續往下執行 |
| **Vacuous pass**｜空洞的通過（Vacuous Pass） | a suite that says OK because the meaningful tests skipped or never ran｜測試報告顯示綠燈過關，但實際上核心測試案例早就被 Skip 掉或是壓根沒跑 |
| **Deferred-work residue**｜「之後補」的殘骸 | a "follow-up commit" comment that never landed｜Code 裡面寫著 `// TODO` 說下個 commit 會補齊，結果過了好幾年都沒人處理 |
| **Rename residue**｜重構改名殘骸 | a consumer still bound to the old name｜核心變數或 Function 已經改名，但角落還殘留著綁定舊名稱的呼叫端 |
| **Diagnosis without probe**｜沒實測就盲目診斷 | a cause concluded from an error message, not a direct check｜遇到 Error 只憑空印出來的字串猜原因，完全沒有深入探查底層真實狀況 |
| **Boundary schema drift**｜邊界結構漂移 | a payload acted on before its shape and type are validated｜跨系統傳進來的 Payload 資料，連資料結構跟型別都還沒驗證就直接拿來跑邏輯 |
| **Cascade / retry storm**｜連鎖失敗／重試風暴 | one step's failure or retry becomes a crash, duplicate write, or orphaned side effect｜單一步驟出錯或發起 Retry，結果一路引爆系統崩潰、資料重複寫入，或是留下沒清乾淨的副作用 |
| **Orphan capability**｜孤兒功能（designed-but-unbuilt，已設計但未串接） | a class, table, column or design-document promise with no caller, no writer, no page and no gap-register row｜Class、資料庫表格、欄位或設計文件中的承諾，沒有任何呼叫者、寫入者、網頁，也沒有記錄在缺口登記表中 |
| **Scope shadow**｜範圍陰影（Scope Shadow） | an audit of one diff or module whose report reads as whole-system green｜明明只審查了單一 Diff 或模組，報告讀起來卻像是整個系統都綠燈放行 |
| **Corner disagreement**｜四角分歧（Corner Disagreement） | customer, operator, logistics provider and payment gateway describe one order differently; or a built method is not reachable under the shipped configuration｜消費者、營運人員、物流商與金流商對同一筆訂單狀態認定不一致；或是已開發的付款方式在目前發布的設定下根本無法到達 |
| **Hosted-surface control**｜託管頁面控制無效（Hosted-Surface Control） | a shop setting claims to restrict a choice the buyer makes on the gateway's own page, where the request cannot express it｜商店後台設定宣稱能限制買家在金流商託管頁面上的選擇，但 API 請求根本無法傳達該限制 |
| **Sampled, not enumerated**｜採樣代替窮舉（Sampled, Not Enumerated） | one payment × delivery cell read and generalised to the grid; a later finding disproves the method, not just the answer｜僅測試了「付款 × 物流」矩陣中的單一格子就推論整張網格正常；後續的發現推翻的是整套檢查方法，而不只是那一格的答案 |
| **Environment constraint never crossed**｜環境約束未交集（Environment Constraint Never Crossed） | a gateway's requirement on the host (fixed egress IP, cron, persistent disk) and the launch host's capability both written down, never multiplied｜金流商對主機的要求（固定 Outbound IP、Cron 排程、持久化磁碟）與上線主機的能力都有記載，但從未進行交叉比對驗證 |
| **Service-variant confusion**｜服務類型混淆（Service-Variant Confusion） | 取貨付款 vs 取貨不付款, platform vs direct, B2C vs C2C — same carrier, different caps, fees and templates, audited as one｜取貨付款 vs 取貨不付款、平台型 vs 獨立型、B2C vs C2C —— 同一家物流商卻有不同的上限、費率與單據樣式，卻被當作同一種服務審查 |
| **Blind instrument**｜盲目儀表（Blind Instrument） | the settlement reconcile or capture sweep stopped running or examined nothing, and the report looked identical to a clean one｜對帳或請款的掃描腳本停止運作或根本沒檢查任何東西，產出的報告卻跟沒有問題時一模一樣 |
| **Unrendered surface**｜未渲染介面（Unrendered Surface） | a state the system can reach has no screen, or one nobody rendered, or one no person can dismiss — so "ignore" happens by default｜系統可能達到的狀態沒有對應的畫面、或是沒人渲染該畫面、或是沒有人能關閉該畫面 —— 導致預設直接「忽略」 |
| **Vacuous or too-late proof**｜空洞或過遲的驗證（Vacuous or Too-Late Proof） | a test asserting emptiness passes for an unrelated reason; or the guard sits so deep in a slow suite nobody reaches it｜斷言「空值」的測試因無關原因通過；或是防禦機制放在太慢的測試套件深處導致根本沒人執行到 |

Prompt with any of those terms, or "audit the wiring and runtime behaviour, not the code", and the sweeps run first.

> 只要你的 Prompt 裡出現上面任何一個術語，或是提到「幫我稽核邏輯接線跟實際行為，不要只看程式碼表面」，這個掃描流程就會自動啟動。

## Which channel each sweep walks｜每個掃描項目對應的 VSM 通道

Each defect class above is a broken channel between two VSM systems; the sweeps are organised by channel, not by file:

> 每一個 Bug 本質上都是兩個 VSM 子系統之間斷裂的通道；因此所有掃描都是按照「通道」來劃分，而不是按檔案目錄分類：

| Channel｜溝通通道 | Sweeps that walk it｜負責掃描這條通道的檢查項 |
|---|---|
| System 3 → System 1 (control to consumer)｜管理層到執行端（Control to Operations） | dead control, deferred-work residue, stale snapshot |
| System 1 → System 1 across time｜跨時間維度（Across Time） | TOCTOU race, rename residue |
| System 4 ↔ environment｜對外部環境（To Environment） | semantic drift, boundary schema drift |
| System 3\* → System 3｜獨立稽核對管理層（Audit to Control） | vacuous pass, diagnosis without probe |
| System 5 defaults｜政策預設機制（Policy Defaults） | fail-open, cascade / retry storm |
| System 3 → System 4 (a setting that must reach the provider's page)｜System 3 → System 4（必須傳達到金流商頁面的設定） | hosted-surface control, sampled-not-enumerated, service-variant confusion｜託管頁面控制無效（hosted-surface control）、採樣代替窮舉（sampled-not-enumerated）、服務類型混淆（service-variant confusion） |
| System 4 requirement × launch host｜System 4 需求 × 上線主機 | environment constraint never crossed｜環境約束未交集（environment constraint never crossed） |
| System 3\* on itself (is the safety net still looking?)｜System 3\* 對自身的監控（安全網是否還在運作？） | blind instrument, vacuous or too-late proof｜盲目儀表（blind instrument）、空洞或過遲的驗證（vacuous or too-late proof） |
| Customer × operator × logistics × gateway｜消費者 × 營運人員 × 物流商 × 金流商 | corner disagreement (the four-corner walk), terminal-state accountability｜四角分歧（corner disagreement，即四角走位）、終態責任歸屬（terminal-state accountability） |
| System 1 → a screen someone opens｜System 1 → 人員開啟的畫面 | unrendered surface, orphan capability, scope shadow｜未渲染介面（unrendered surface）、孤兒功能（orphan capability）、範圍陰影（scope shadow） |

A channel on the map with no sweep site named against it is reported as unswept.

> 只要架構圖上有任何一條通道沒有被掃描點覆蓋到，報告就會直接將其標示為「未掃描」。
