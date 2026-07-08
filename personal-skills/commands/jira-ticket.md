---
description: "Read Jira ticket, implement task, then auto-commit via /pre-commit-review. Use when the user provides a Jira ticket number (e.g. PROJ-1234) and wants to implement it end-to-end."
argument-hint: "<Jira ticket，例：PROJ-1234>"
---

# Jira Ticket

Implement the task described in Jira ticket **`$ARGUMENTS`**, then commit via the pre-commit-review workflow.

> ⚠️ **CRITICAL — 嚴格按步驟執行**
> - Step 4（`/opsx:propose`）是**強制閘門**，未執行並等到使用者確認 `tasks.md` 之前，**禁止修改任何原始碼**
> - 每個 Step 必須依序完成，不得跳過
> - 禁止在 Step 4 完成前進行任何 `Edit`、`Write`、`Bash` 寫檔操作

---

## Step 0 — Load agent standards

Read the following agent file before doing anything else:
- `{{HOME}}/.claude/agents/engineering-minimal-change-engineer.md`

Then check the repo root:
```bash
git rev-parse --show-toplevel
```
If the path starts with `{{PROJECT_REPO}}`, also read:
- `{{HOME}}/.claude/agents/{{PROJECT_CONVENTIONS_AGENT}}`

Keep all rules in mind throughout implementation.

---

## Your Role — 縝密執行者

- 每一步做完整，不跳過、不猜測
- 執行中看到問題，**主動說出來**，不是等使用者發現
- 有疑問先問再做，不是猜測後執行
- 如果你認為某個做法有問題或不合理，說出來，不是默默照做完
- 在實作過程中如有疑問，可隨時呼叫 `/quality-gate mentor-check-plan` 讓 Mentor 協助確認方向

---

## Step 1 — Authenticate with Atlassian MCP

Use the Atlassian MCP tools to connect to Jira.

- If already authenticated, skip to Step 2.
- If not authenticated, trigger the authentication flow and wait for it to complete before proceeding.

---

## Step 2 — Fetch the ticket

Use the Atlassian MCP to fetch Jira issue **`$ARGUMENTS`**.

Extract and summarise:
- **Summary** — one-line description of the task
- **Issue type** — Bug / Story / Task / Sub-task
- **Description** — detailed description and requirements
- **Acceptance criteria** — what "done" means
- **Priority / labels** — any extra context

Print a compact summary so the user can see what is being implemented.

Determine the nature of the work from the issue type and description:
- **Bug** → root-cause fix, minimal change
- **Story / Feature** → new functionality per spec
- **Task / Chore** → refactor, cleanup, config change, etc.

If the ticket description contains a **Figma link**, fetch the design context using the Figma MCP tool (`get_design_context`). Extract color tokens, spacing, typography, component structure, and interaction behaviour.

If the ticket description contains a **Confluence link**, fetch the page content using the Atlassian MCP tool (`getConfluencePage`). Extract functional requirements, flow descriptions, and acceptance criteria.

---

## Step 2.2 — Search for matching superpowers spec

After fetching the ticket, search for any spec files that match the ticket number:

```bash
find docs/superpowers/specs/ -name "*$(echo $ARGUMENTS | tr '[:upper:]' '[:lower:]')*" 2>/dev/null
```

- **If matching files found**: read their content and announce it. Use as the **primary reference** when generating the proposal in Step 4.
- **If none found**: continue silently.

---

## Step 2.5 — Clarify before implementing

Before writing any code, identify anything **genuinely ambiguous** — meaning there is a real decision only the user can make:
- Behaviour explicitly missing from the ticket
- Multiple valid approaches with meaningfully different trade-offs
- Design details not visible without a linked design file

**Stop and ask the user** about each such point. Do NOT ask to confirm logical deductions derivable from the ticket + existing code.

---

## Step 3 — Find the relevant code

Use `Grep`, `Glob`, and `Read` to locate the files and code paths related to the ticket.

- Search for identifiers, error messages, or keywords from the ticket description.
- Read the relevant files to understand the current implementation.
- **Before adding any new class, method, or storage, explicitly survey what already exists.** Only propose net-new structures after confirming existing ones are insufficient.

### Bug tickets — mandatory root cause gate ⛔

If the issue type is **Bug**, invoke `superpowers:systematic-debugging` and complete **Phase 1 (Root Cause Investigation) through Phase 3 (Hypothesis and Testing)** before proceeding to Step 4.

⛔ **Do NOT proceed to Step 4 until the root cause is confirmed.**

---

## Step 4 — Create OpenSpec change ⛔ 強制閘門

**禁止跳過。禁止在此步驟完成前修改任何原始碼。**

First, check whether a change for this ticket already exists:

```bash
ls openspec/changes/ | grep "$(echo $ARGUMENTS | tr '[:upper:]' '[:lower:]')-"
```

- **If matches found**: show the list and ask the user which to reuse, or create a new one.
- **If none found**: proceed below.

Before calling `/opsx:propose`, read agent files (already loaded in Step 0). If `{{PROJECT_CONVENTIONS_AGENT}}` is set, pay special attention to its class design and module placement rules when writing the proposal.

Invoke `/opsx:propose` to generate the spec files.

- Change name format: `<ticket-lower>-<short-description>` (e.g. `proj-1234-add-login-button`)
- The proposal, design, and tasks.md will be created under `openspec/changes/<name>/`

⛔ **tasks.md 產出後，立即執行 mentor-check-plan，禁止先展示給使用者：**

```bash
python3 ~/.claude/tools/mentor_memory.py init
```

Then invoke `/quality-gate mentor-check-plan <ticket-number> <tasks-md-path>`

- **PASS / WARN** → 繼續，展示 tasks.md 給使用者確認
- **BLOCK** → 修正 task list 後重跑，不得跳過

⛔ **STOP：在使用者明確確認 tasks.md 後才能繼續 Step 4.3。**

---

## Step 4.3 — PR Phase Planning

根據確認後的 tasks.md，判斷是否需要分 phase 發 PR。

| 條件 | 建議 |
|---|---|
| tasks ≤ 3 個 | 單一 phase |
| tasks ≥ 4 個但都在同一個 layer | 單一 phase |
| tasks 跨越 data / domain / UI 層 | 分 phase |
| 有明確依賴順序 | 依依賴分 phase |

**預設 2-phase 切法（跨 layer 時）：**
- Phase 1：data + domain layer
- Phase 2：UI layer

提出建議並詢問使用者確認後才進入 Step 4.5。

---

## Step 4.5 — Confirm branch strategy

Before touching any code, confirm the branch strategy with the user:

```
實作前先確認分支策略：

目前分支：<git branch --show-current>
建議：<根據 ticket 情況給出建議>

A) 從 main / develop 新建功能分支
B) 從現有分支繼續
C) 直接在目前分支作業
```

若 `{{PROJECT_CONVENTIONS_AGENT}}` 有定義分支命名規則，依照其格式建議分支名。

Wait for the user's answer, then execute the corresponding `git checkout`.

**Multi-phase：** Phase 1 從 base branch 開，Phase N 從 Phase N-1 開。此步驟只建立當前 phase 的 branch。

---

## Step 5 — Implement

First, transition the Jira ticket to "In Progress":

1. Call `getTransitionsForJiraIssue` on **`$ARGUMENTS`** to list available transitions.
2. Find the "In Progress" transition and call `transitionJiraIssue`.

Then invoke `/opsx:apply` to implement the tasks defined in `tasks.md` one by one.

**Multi-phase：** 只實作當前 phase 的 tasks，不得跨 phase 實作。

**Pivot 同步：** 每完成一個 task，若實作方式與 `tasks.md`、`spec.md`、`design.md` 描述不同，立即更新 openspec 文件，只描述最終行為。

---

## Step 5.5 — Phase Checkpoint

當前 phase 所有 tasks 完成後，詢問使用者：

> Phase N 的 tasks 已全部完成。要現在執行 review 並發 PR 嗎？
>
> A) 是 → 執行 Step 6（/pre-commit-review），完成後執行 /write-pr
> B) 否 → 直接繼續下一個 Phase

若為單一 phase 或最後一個 phase：跳過此 checkpoint，直接進入 Step 6。

---

## Step 6 — Run pre-commit-review

Read the file `{{HOME}}/.claude/commands/pre-commit-review.md` and follow **all its steps** from Step 1 through Step 7, passing **`$ARGUMENTS`** as the ticket number.

---

## Step 7 — Ask about PR

After the commit succeeds, ask the user:

```
要發 PR 嗎？說 yes 我會執行 /write-pr $ARGUMENTS。
```

- If yes: invoke `/write-pr $ARGUMENTS`.
- If no: end the workflow.
