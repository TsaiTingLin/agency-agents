---
description: "Full flow from requirement to Jira ticket — includes built-in brainstorming, so do NOT separately invoke superpowers:brainstorming. Use when the user wants to create a Jira ticket or Epic for a new feature, bug, or technical task."
argument-hint: "[需求描述（可選）]"
---

# New Jira Ticket

從原始需求到建立 Jira ticket（或 Epic）的完整前置流程。

---

## 前置條件

本 skill 需要以下 env 變數（透過 `local.env` + `sync-skills.sh` 注入）：

| 變數 | 用途 |
|---|---|
| `{{JIRA_PROJECT_KEY}}` | Jira 專案鍵值（例：`H2S`、`PROJ`） |
| `{{JIRA_BASE_URL}}` | Jira 實例 URL（例：`https://yourcompany.atlassian.net`） |
| `{{JIRA_ASSIGNEE_EMAIL}}` | 指派人 email |

若 `{{PROJECT_CONVENTIONS_AGENT}}` 有設定，建票時會讀取以取得專案特定格式（ticket 前綴、label、架構原則等）。

---

## 內嵌規則（本 skill 專用）

**Jira ticket 格式：**
- Summary 必須是英文，**總長不超過 60 字元**
- 若 conventions agent 有定義 summary 前綴（例：`[Android]`），加上；否則不加
- Project：`{{JIRA_PROJECT_KEY}}`
- Assignee：使用 `lookupJiraAccountId` 查 `{{JIRA_ASSIGNEE_EMAIL}}` 取得帳號 ID
- Label：若 conventions agent 有定義預設 label，使用；否則不加
- Issue type：**Task**（預設）/ Bug / Epic — 盡量避免使用 Story

**Epic 格式（若需要）：**
- Child tickets 各自建立並 link 到 Epic

**設計文件路徑：**
- Brainstorm spec 暫定名稱：`docs/superpowers/specs/YYYY-MM-DD-<topic>-design.md`
- 建票後 rename：`docs/superpowers/specs/YYYY-MM-DD-<project-key>-XXXX-<topic>-design.md`

**Brainstorming 覆蓋規則：**
- 完成後**不要**呼叫 `writing-plans`
- 繼續執行本 skill 的後續步驟

**架構設計原則：**
- Brainstorming 開始前讀取 `{{HOME}}/.claude/agents/engineering-minimal-change-engineer.md`
- 若有 `{{PROJECT_CONVENTIONS_AGENT}}`，一併讀取以了解專案架構慣例
- 提案時優先問「能擴充現有的嗎？」再考慮新建
- 不要為假設性需求建抽象層

---

## Step 1 — 收集背景材料

詢問使用者提供以下任何相關素材（有什麼給什麼，不必全有）：

> 「在開始之前，請提供任何相關背景資料：
> - Confluence 文件連結
> - Figma 設計連結
> - Slack 討論連結（貼 URL 即可，無需截圖或貼文內容）
> - Bug 重現步驟或錯誤描述
> - PRD / 規格文件
> - 其他參考資料
>
> 有什麼給什麼，沒有的跳過沒關係。」

收到材料後：
- **Confluence 連結** → 用 Atlassian MCP `getConfluencePage` 讀取
- **Figma 連結** → 用 Figma MCP `get_design_context` 讀取
- **Slack URL** → 將連結附在 ticket description 的「相關連結」區塊作為參考
- **純文字描述** → 直接使用

列出已收集到的材料摘要再繼續。若 `$ARGUMENTS` 有提供描述，帶入並跳過詢問。

---

## Step 1.5 — 搜尋既有相關 ticket

根據 Step 1 收集到的需求描述，提取 **3-5 個關鍵字**，分兩輪搜尋：

**第一輪**（full-text）：
```
project = {{JIRA_PROJECT_KEY}} AND status != Done AND text ~ "<關鍵字1>"
```

**第二輪**（僅搜 summary）：
```
project = {{JIRA_PROJECT_KEY}} AND status != Done AND summary ~ "<關鍵字2>"
```

兩輪結果合併去重後呈現：
- **找到疑似相關** → 列出並詢問：「這幾張是否已包含你要做的事，還是仍需要新建？」等確認後再繼續
- **無相關** → 直接進 Step 2，不需告知使用者

---

## Step 2 — Brainstorming

使用 `superpowers:brainstorming` skill，帶入 Step 1 收集到的所有材料。

遵守本 skill 的覆蓋規則：結束後不呼叫 `writing-plans`，直接進 Step 3。

**重要：Spec 在討論確認前不得產出。**

Brainstorming 結束後，在寫入 spec 檔之前：

1. 列出設計方向摘要（觸發條件、架構選擇、主要取捨）
2. 詢問使用者：「以上設計方向有沒有需要調整的？確認後我再產出 spec。」
3. 等使用者明確確認後才產出 spec

**確認後，產出 spec 前，執行 cross-check：**

| 狀況 | 處理方式 |
|---|---|
| 來源有、設計草稿沒提到 | 列出，詢問是否要補入設計 |
| 設計草稿有、來源沒提到 | 標注為推論或假設，請使用者確認 |
| 來源描述模糊或有歧義 | 明確指出，請使用者裁定 |

所有疑點確認完畢後，才產出 spec 檔：`docs/superpowers/specs/YYYY-MM-DD-<topic>-design.md`

**Spec 內容邊界：**

| ✅ 放進 spec | ❌ 不放進 spec |
|---|---|
| 背景、目標、範圍 | Code snippet |
| 顯示邏輯、觸發條件 | 函式名稱、欄位名稱、改法步驟 |
| 架構決策（用哪個 pattern、為什麼） | 具體要改哪個 class、哪一行 |
| 資料來源、API 欄位語意 | tasks 清單、TODO 列表 |

**Spec 產出後：**
若有 `{{PROJECT_CONVENTIONS_AGENT}}`，對照其 Module Structure / Architecture 段落做 placement self-check，確認每個新增的 class / module 放在正確位置，有不符的直接修正。

**Brainstorm Gate：**
```
/quality-gate mentor-check-brainstorm <spec-file-path> <Step 1 材料清單>
```
若 BLOCK → 修正 spec 後重跑；PASS / WARN → 繼續 Step 3。

---

## Step 3 — 評估規模

根據設計內容評估規模，請使用者確認：

**單張 ticket（Task / Bug）：**
- 單一功能或明確的技術改動
- 一個 sprint 內可完成

**Epic + 子票：**
- 跨多個模組或功能區塊
- 需要超過一個 sprint

呈現格式：
```
## 規模評估

**建議：** [單張 ticket / Epic + N 張子票]
**原因：** [2-3 句說明]

[若 Epic]
**Epic：** <英文標題>
**子票：**
1. <子票 1>
2. <子票 2>

這樣的拆法符合你的期望嗎？
```

等使用者確認後，判斷 issue type 並請確認：

> 「Issue type 我建議是 **Task / Bug**（原因一句話），確認嗎？」

等確認後，追加詢問 Epic 歸屬（若適用）。記下 Epic 編號，建票後用 `editJiraIssue` 設定 `parent` 欄位。

---

## Step 4 — 建立 Jira ticket(s)

**查詢 Assignee ID：**
```
lookupJiraAccountId: {{JIRA_ASSIGNEE_EMAIL}}
```

**Description 格式（對象：PM、設計師、stakeholder）：**

```
## 背景
（為什麼要做，業務或用戶痛點，用非工程語言說明）

## 需求說明
（What：功能範圍、觸發條件、UI 行為，不提具體技術實作）

## 相關連結
- [平台名稱](url)（若無則省略整個區塊）
```

**禁止放入 Jira description：**
- 類別名稱、函式名稱、模組路徑
- 實作步驟或偽代碼
- 具體的邊界條件與測試情境

每張建立後顯示：
```
✓ {{JIRA_PROJECT_KEY}}-XXXX: <title>
  {{JIRA_BASE_URL}}/browse/{{JIRA_PROJECT_KEY}}-XXXX
```

建票完成後，將 brainstorm spec 檔加入單號：

1. 找到暫定 spec 檔：`docs/superpowers/specs/YYYY-MM-DD-<topic>-design.md`
2. 目標檔名：`docs/superpowers/specs/YYYY-MM-DD-<project-key>-XXXX-<topic>-design.md`
3. 先確認是否已有相同單號的 spec 檔：
   ```bash
   ls docs/superpowers/specs/ | grep -i "<project-key>-XXXX"
   ```
   - **有找到** → 詢問：「找到既有的 spec 檔：`<filename>`，要更新它的內容嗎？」
   - **沒找到** → 直接 rename

若為 Epic + 子票：使用第一張子票的單號命名 spec 檔。

---

## Step 5 — 是否立即實作？

```
已建立：
- {{JIRA_PROJECT_KEY}}-XXXX: <title>

要現在開始實作嗎？說 yes 我會執行 /jira-ticket {{JIRA_PROJECT_KEY}}-XXXX，
或你可以之後再開始。
```

若 yes：執行 `/jira-ticket {{JIRA_PROJECT_KEY}}-XXXX`。
若否：結束流程。
