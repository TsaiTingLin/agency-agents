# quality-gate

Quality Gate Mentor の品質檢查流程。在 skill 執行的關鍵節點呼叫 Mentor 做獨立審查。

## 使用方式

| 何時呼叫 | 指令 |
|---------|------|
| Spec 寫入後（含 `new-jira-ticket`、`new-feature`） | `/quality-gate mentor-check-brainstorm <spec-path> <materials>` |
| 實作計畫產出後（有 Jira） | `/quality-gate mentor-check-plan <ticket> <tasks-md-path>` |
| 實作計畫產出後（無 Jira） | `/quality-gate mentor-check-plan none <plan-path>` |
| Commit 之前 | `/quality-gate mentor-check-commit <ticket-or-none> <tasks-md-path>` |

---

## Observer Protocol

適用所有使用 Mentor Check 的 code 相關 skill。

**使用者只在兩個時間點介入：**
1. **mentor-check-plan 通過後** — 使用者確認 tasks.md
2. **pre-commit-review 完成後** — 使用者確認 commit message

**其餘三個 Mentor Check 由 Claude + Mentor 自主完成，不詢問使用者。**

### 對話顯示格式

每次 Mentor Check 互動必須以下列格式輸出，讓使用者觀看進度：

```
Claude：[意圖說明]
Mentor：[PASS / WARN / BLOCK + 理由摘要]
```

- **PASS / WARN** → Claude 立即執行，不詢問使用者
- **BLOCK** → Claude 自主修正後重送 Mentor，直到 PASS 為止
- **ESCALATE** → Claude 將 Mentor 的問題轉達給使用者，等待回答後重送 Mentor

### 錯誤記錄

過程中任何問題，立即記錄至 session：

```bash
python3 ~/.claude/tools/mentor_memory.py log-issue '問題描述' '發生原因' '解法'
```

issues.md 供 mentor-check-commit retrospective 讀取。關閉 terminal 後由 EXIT trap 自動清除。

---

## mentor-check-brainstorm — Spec 正確性驗證

呼叫時機：`new-jira-ticket` brainstorming 確認後、spec 寫入磁碟後，進入 Step 3 之前。

```
Agent(
  subagent_type = "engineering-quality-gate-mentor",
  prompt = """
你正在執行 mentor-check-brainstorm。

從 Step 1 收集到的原始素材：
  Confluence：<url>（若無則省略）
  Figma：<url>（若無則省略）
  若無任何外部素材，使用者的原始需求描述：
    <逐字貼上使用者在對話裡說的需求>

Spec 草稿路徑：<spec-file-path>

步驟：
1. 用 Atlassian MCP / Figma MCP 自己讀上方的原始素材（有哪個讀哪個，不接受 implementer 摘要）
   若無外部素材，直接從使用者原始描述工作
2. 讀 <spec-file-path>
3. 逐段比對，找出：
   a. 原始素材有、spec 沒提到的需求
   b. Spec 有、原始素材找不到依據的推論（標記「待確認假設」）
   c. 素材描述清楚但 spec 理解有誤的地方
4. 輸出 MENTOR-CHECK-BRAINSTORM RESULT
"""
)
```

若 BLOCK → 修正 spec 後重跑；PASS / WARN → 繼續 Step 3。

---

## mentor-check-plan — 計畫完整性驗證

呼叫時機：實作計畫（tasks.md / plan.md）產出後、使用者確認之前。

**`ticket` 參數：**
- 有 Jira → 填 ticket 編號（例 `H2S-1234`）
- 無 Jira → 填 `none`

**同時做兩件事：**
1. 對照需求來源驗需求覆蓋（有 Jira → 讀 Jira；無 Jira → 以 brainstorm spec 為需求來源）
2. 對照 brainstorm spec 驗技術內容（若有 spec）

**步驟：**

1. 初始化 session：
   ```bash
   python3 ~/.claude/tools/mentor_memory.py init
   ```

2. 呼叫 Mentor：
   ```
   Agent(
     subagent_type = "engineering-quality-gate-mentor",
     prompt = """
   你正在執行 mentor-check-plan。

   Ticket：<ticket-number>（若為 none 則跳過所有 Jira 步驟）
   Tasks/Plan 路徑：<tasks-md-path>
   Brainstorm spec 路徑：<spec-path>（若無則省略此行）

   步驟：
   1. 若 ticket ≠ none：
      用 Atlassian MCP 自己讀 Jira ticket <ticket-number> 全文，不接受任何摘要
      若 ticket = none：
      跳過此步驟；需求來源為 brainstorm spec（步驟 2）
   2. 若有 brainstorm spec：
      - 讀取 <spec-path>（已通過 mentor-check-brainstorm 驗證，為技術設計的 source of truth）
      若無 brainstorm spec 且 ticket = none：
      - BLOCK：「無 Jira ticket 也無 brainstorm spec，無法驗證需求覆蓋」
      若無 brainstorm spec 且 ticket ≠ none：
      - 警告：「無 brainstorm spec，技術設計決策只能從 Jira 推斷，風險較高」
   3. 整理需求清單：
      - 若有 Jira：業務需求來自 Jira，技術設計決策來自 brainstorm spec（若有）
      - 若無 Jira：需求清單完全來自 brainstorm spec
   4. 把清單寫入 session：
      python3 ~/.claude/tools/mentor_memory.py write-requirements '<內容>'
   5. 讀 <tasks-md-path>，以及同目錄下的 spec.md / design.md（若存在）
   6. 逐條比對：
      a. Tasks/Plan 有沒有涵蓋所有需求？（Jira 或 spec 來的都算）
      b. Tasks/Plan 有沒有符合 brainstorm spec 的技術設計方向？（若有 spec）
      c. Spec.md / design.md 的技術內容和 brainstorm spec 一致嗎？（若有）
   7. 輸出 MENTOR-CHECK-PLAN RESULT
   """
   )
   ```

3. 根據結果：
   - **PASS / WARN** → 展示 tasks.md / plan 給使用者確認
   - **BLOCK** → 修正後重跑；**ESCALATE** → 轉達使用者後重跑

---

## mentor-check-commit — 最終交付確認

呼叫時機：`pre-commit-review` Step 5.5，commit 之前。

```
Agent(
  subagent_type = "engineering-quality-gate-mentor",
  prompt = """
你正在執行 mentor-check-commit。

Ticket：<ticket-number>
Tasks.md 路徑：<tasks-md-path>

步驟：
1. 用 Atlassian MCP 自己讀 Jira ticket <ticket-number> 全文，不接受任何摘要
2. 讀 <tasks-md-path>，找出所有 [x] 已完成的 task，忽略 [ ] 未完成的 task
3. 讀 session 的 mentor-log.md：
   python3 ~/.claude/tools/mentor_memory.py read-log
4. 執行 git diff HEAD 取完整 diff
5. 逐條核對每個 [x] task：diff 是否真的完成了這個 task？
6. 從 Jira 逐條核對每個需求：
   - [x] tasks 有覆蓋到嗎？
   - diff 有沒有改到 [ ] tasks 的範圍（超出當前 phase）？
7. 掃描跨檔案一致性
8. 輸出 MENTOR-CHECK-COMMIT RESULT

若無 Jira ticket（ticket = none）：跳過步驟 1、6，只做步驟 2、3、4、5、7
"""
)
```

### Retrospective（PASS 後執行）

1. 讀取本次 session 問題記錄：
   ```bash
   python3 ~/.claude/tools/mentor_memory.py read-issues
   ```
2. 逐行看「解法」欄：一次性問題 → 略過；普遍原則 → 提案更新 agent 或 skill
3. 向使用者說明提案，等明確確認後再執行更新
4. 更新完成後告知使用者：可關閉 terminal，EXIT trap 自動刪除 session 記憶

---

## 注意事項

- `engineering-quality-gate-mentor` agent 必須已安裝於 `~/.claude/agents/`
- `~/.claude/tools/mentor_memory.py` 必須存在且可執行
- `ANTHROPIC_API_KEY` 必須在 shell 環境中
