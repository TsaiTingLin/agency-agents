---
description: "Full flow from requirement to commit — brainstorm, plan, implement, review, commit. No Jira required. Use when starting any new feature, bug fix, or technical task."
argument-hint: "[需求描述（可選）]"
---

# New Feature

從需求到 commit 的完整流程：收集材料 → brainstorm → 實作計畫 → 找相關 code → 實作 → review → commit。

> ⚠️ **每個 Step 必須依序完成，不得跳過**

---

## Step 0 — 讀取專案慣例

在做任何事之前，若有設定 `{{PROJECT_CONVENTIONS_AGENT}}`，先讀取：

```
{{HOME}}/.claude/agents/{{PROJECT_CONVENTIONS_AGENT}}
```

整個 skill 執行過程中持續遵守其規則。

---

## Step 1 — 收集背景材料

詢問使用者提供任何相關素材（有什麼給什麼，不必全有）：

> 「在開始之前，請提供任何相關背景資料：
> - Confluence / 文件連結
> - Figma 設計連結
> - Slack 討論連結
> - Bug 重現步驟或錯誤描述
> - PRD / 規格文件
> - 其他參考資料」

收到材料後：
- **Confluence 連結** → 用 Atlassian MCP `getConfluencePage` 讀取
- **Figma 連結** → 用 Figma MCP `get_design_context` 讀取
- **純文字描述** → 直接使用

列出已收集到的材料摘要再繼續。若 `$ARGUMENTS` 有提供描述，帶入並跳過詢問。

---

## Step 2 — Brainstorming

使用 `superpowers:brainstorming` skill，帶入 Step 1 收集到的所有材料。

**覆蓋規則：**
- 結束後**不**呼叫 `writing-plans`，直接進 Step 3

**Spec 產出前（必須先確認）：**
1. 列出設計方向摘要（架構選擇、主要取捨）
2. 詢問：「以上設計方向有沒有需要調整的？確認後我再產出 spec。」
3. 等使用者明確確認後才產出 spec

**Cross-check（spec 產出前）：**

| 狀況 | 處理方式 |
|---|---|
| 來源有、spec 沒提到 | 列出，詢問是否補入 |
| Spec 有、來源找不到依據 | 標注為假設，請使用者確認 |
| 來源描述模糊或有歧義 | 指出，請使用者裁定 |

所有疑點確認後，產出 spec：`docs/superpowers/specs/YYYY-MM-DD-<topic>-design.md`

**Placement self-check（spec 產出後）：**
若有 `{{PROJECT_CONVENTIONS_AGENT}}`，確認每個新增的 class / module 放在正確位置，不符的直接修正。

**Brainstorm Gate：**
```
/quality-gate mentor-check-brainstorm <spec-file-path> <Step 1 材料清單>
```
若 BLOCK → 修正 spec 後重跑；PASS / WARN → 繼續 Step 3。

---

## Step 3 — 實作計畫

**3.1 — 規模評估**

根據 spec 評估並請使用者確認：

```
建議：[單一功能 / 多階段]
原因：[2-3 句說明]

這樣的範圍符合你的期望嗎？
```

**3.2 — 產出實作計畫**

使用 `superpowers:writing-plans`，以 spec 為輸入，產出 implementation plan。

Plan 路徑：`docs/superpowers/plans/YYYY-MM-DD-<topic>-plan.md`

**覆蓋規則：writing-plans 產出 plan 後，不執行 subagent-driven-development 或 executing-plans，控制權回本 skill。**

**3.3 — Plan Gate**

```
/quality-gate mentor-check-plan none <plan-path>
```

若 BLOCK → 修正 plan 後重跑；PASS / WARN → 展示 plan 給使用者確認。

⛔ **等使用者明確確認 plan 後，才進入 Step 4。**

---

## Step 4 — 找相關 code

用 Grep、Glob、Read 找到與功能相關的檔案與 code path：

- 根據需求描述搜尋關鍵字、class 名稱、函式名稱
- 讀相關檔案，理解現有實作
- **新增任何 class、method、storage 前，先確認 codebase 是否已有可擴充的現有實作**，只有在確認現有實作不足後才提新結構

若需求類型是 **Bug**，先執行 `superpowers:systematic-debugging` 完成根因確認，再繼續。

---

## Step 5 — 確認分支策略

實作前確認要在哪個 branch 上進行：

```
實作前先確認分支策略：

A) 從 main / develop 新建功能分支
B) 從現有分支繼續
C) 直接在目前分支作業

目前分支：<git branch --show-current>
建議：<根據 plan 範圍給出建議>
```

等使用者確認後執行對應的 `git checkout`。

**多階段（若 Step 3.1 確認多階段）：**
- Phase 1 從 base branch 開
- Phase N 從 Phase N-1 branch 開
- 此步驟只建立**當前 Phase** 的 branch

---

## Step 6 — 實作

依照 plan 的 tasks 逐一完成。每完成一個 task：
- 若實作方式與 plan 描述有出入（例如 signature 改變、新增依賴），**立即更新 plan**，反映最終實作

過程中若有疑問：
```bash
python3 ~/.claude/tools/mentor_memory.py log-issue '問題描述' '發生原因' '解法'
```

**多階段注意**：只實作**當前 Phase** 的 tasks，不得跨 phase 實作。

---

## Step 6.5 — Phase Checkpoint（多階段才執行）

當前 Phase 所有 tasks 完成後：

> Phase N 的 tasks 已全部完成。
> 要現在執行 review 並 commit 嗎？
>
> A) 是 → 執行 Step 7
> B) 否 → 直接繼續下一個 Phase（回到 Step 5 建新 branch → Step 6）

若為單一 Phase 或最後一個 Phase：跳過此 checkpoint，直接進 Step 7。

---

## Step 7 — Review 與 Commit

執行 `/pre-commit-review <plan-path>`，完整跑完其所有步驟（review → fix → test → mentor-check-commit → commit）。

`<plan-path>` 為 Step 3.2 產出的 plan 檔路徑，傳入後 mentor-check-commit 會用它做計畫覆蓋驗證。

---

## Step 8 — Retrospective

Commit 完成後：

1. 讀取 session 問題記錄：
   ```bash
   python3 ~/.claude/tools/mentor_memory.py read-issues
   ```
2. 逐行看「解法」欄：一次性問題 → 略過；普遍原則 → 提案更新 agent 或 skill
3. 向使用者說明提案，等明確確認後再執行更新
4. 更新完成後告知使用者：可關閉 terminal，EXIT trap 自動刪除 session 記憶
