---
description: "Read Jira tickets, analyze git diff, generate PR description and create PR. Use when the user wants to open a GitHub PR and needs the description generated from Jira tickets."
argument-hint: "<PROJ-1234> [PROJ-5678] [--into main]"
---

# Write PR Description

根據提供的 Jira ticket 與目標分支，自動抓取 ticket 內容、分析 git diff，產生 PR description，並直接建立 GitHub PR。

**參數格式：** `PROJ-1234 PROJ-5678 --into main`
如果沒有給 `--into`，**不要自行假設 base branch，必須詢問使用者**。

---

## Step 1 — 解析參數與偵測分支

若有設定 `{{PROJECT_CONVENTIONS_AGENT}}`，先讀取以取得專案特定 PR 規則（如 PR Labels 規則、必填欄位）：
```
{{HOME}}/.claude/agents/{{PROJECT_CONVENTIONS_AGENT}}
```

```bash
git branch --show-current
git branch -r | grep -E "develop|main|master|release" | head -10
```

從 `$ARGUMENTS` 中提取所有 ticket 號碼（格式：`{{JIRA_PROJECT_KEY}}-XXXX`，可能有多個）。

**Base branch 判斷：**
1. 若 `$ARGUMENTS` 有 `--into <branch>`，使用指定的
2. 否則停下來問使用者，並列出遠端候選清單

確認後印出摘要再繼續：
```
Head branch : <head-branch>
Base branch : <base-branch>
Tickets     : {{JIRA_PROJECT_KEY}}-XXXX, {{JIRA_PROJECT_KEY}}-YYYY
```

---

## Step 2 — 抓取 Jira tickets

用 Atlassian MCP 逐一抓取每個 Jira ticket：
- cloudId: `{{JIRA_WORKSPACE_ID}}`
- fields: `["summary", "description", "comment", "acceptance criteria"]`

從每個 ticket 的 `comment.comments` 取**第一則留言**的 `id`，組出測試連結：
```
{{JIRA_BASE_URL}}/browse/{{JIRA_PROJECT_KEY}}-XXXX?focusedCommentId=<first comment id>
```
若沒有任何留言，Test 欄位寫「待補」。

---

## Step 3 — 分析 git 變更

```bash
git branch --show-current
git log origin/<base-branch>..HEAD --oneline
git diff origin/<base-branch>...HEAD --stat
git diff origin/<base-branch>...HEAD --name-only --diff-filter=A
```

---

## Step 4 — 產生 PR description

根據 Jira issue type 判斷 template：
- **Bug** → 使用 Bug Template
- **其他** → 使用 Feature Template

共同規則：
- PR 標題格式：`[Jira {{JIRA_PROJECT_KEY}}-XXXX][Jira {{JIRA_PROJECT_KEY}}-YYYY]... <ticket summary>`
- Ticket 連結格式：`[Jira {{JIRA_PROJECT_KEY}}-XXXX]({{JIRA_BASE_URL}}/browse/{{JIRA_PROJECT_KEY}}-XXXX)`
- Review Requirements 預設填 `2`

若 `{{PROJECT_CONVENTIONS_AGENT}}` 有定義額外必填欄位（例如：product area、feature flag），補在 description 最後。

---

### 📛 Bug Template

```markdown
## Jira information

### Issue link/message
（若 ticket description 有相關連結則填入，否則留空）

### Ticket
[Jira {{JIRA_PROJECT_KEY}}-XXXX]({{JIRA_BASE_URL}}/browse/{{JIRA_PROJECT_KEY}}-XXXX) <ticket summary>

## Bug description
（從 ticket description 整理 bug 現象）

## Steps to reproduce
（從 ticket 整理復現步驟）

## Root cause
（從 ticket 整理 root cause）

## Solution
（從 git diff 推斷 solution）

## Does it impact any other area of the project?
- [x] No

## Describe what've you done to test the issue?
> - [x] （從 ticket / git diff 整理測試項目）

## Describe what steps you can provide to test the issue?
> - [x] [測試]({{JIRA_BASE_URL}}/browse/{{JIRA_PROJECT_KEY}}-XXXX?focusedCommentId=XXXXX)

## Review Requirements
=2 reviewers.

[{{JIRA_PROJECT_KEY}}-XXXX]: {{JIRA_BASE_URL}}/browse/{{JIRA_PROJECT_KEY}}-XXXX
```

---

### ✨ Feature Template

```markdown
### Ticket
[Jira {{JIRA_PROJECT_KEY}}-XXXX]({{JIRA_BASE_URL}}/browse/{{JIRA_PROJECT_KEY}}-XXXX)

### Backlog
（直接貼上 Jira ticket description 的「背景」與「需求說明」原文，保留原格式，不要改寫或摘要）

### How did you implement the feature?
- （從 git diff 新增的檔案/class 推斷，保持簡潔）

### Does it impact any other area of the project?
No

### Describe what've you done to test the feature?
- [測試]({{JIRA_BASE_URL}}/browse/{{JIRA_PROJECT_KEY}}-XXXX?focusedCommentId=XXXXX)
  - （測試項目）

### Review Requirements
2

### Additional information
（若 ticket 有 todo 或後續事項則列出，否則留空）
```

---

## Step 5 — 確認 Labels、Reviewers 並建立 PR

**5.1 — 詢問 Labels**

```bash
gh label list --limit 50 --json name,description \
  --jq '.[] | "- \(.name)" + (if .description != "" then " — \(.description)" else "" end)'
```

根據 ticket 內容與 git 變更推薦 labels，用 **AskUserQuestion tool**（multiSelect: true）讓使用者確認。

**5.2 — 建立 PR**

```bash
gh pr create \
  --base <base-branch> \
  --title "[Jira {{JIRA_PROJECT_KEY}}-XXXX]... <ticket summary>" \
  --reviewer {{PR_REVIEWERS}} \
  --label "<label1>" \
  --body "$(cat <<'EOF'
<generated description>
EOF
)"
```

若無 reviewer 設定，省略 `--reviewer`。若無 label，省略 `--label`。

回傳 PR URL 並記下 PR number。

---

## Step 6 — 背景監聽 CI 狀態與 bot review

**6.1 — 取得基本資訊**

```bash
COMMIT=$(git rev-parse HEAD)
REPO=$(gh repo view --json nameWithOwner -q '.nameWithOwner')
PR=<pr-number>
```

**6.2 — CI 狀態監聽（run_in_background: true）**

```bash
COMMIT=<commit-hash>; REPO=<repo>
while true; do
  STATUSES=$(gh api repos/$REPO/commits/$COMMIT/statuses \
    --jq '[.[] | {context, state}] | unique_by(.context)')
  FAILED=$(echo "$STATUSES" | jq -r '.[] | select(.state == "failure") | .context')
  SUCCESS=$(echo "$STATUSES" | jq -r '[.[] | select(.state == "success")] | length')
  TOTAL=$(echo "$STATUSES" | jq -r 'length')
  if [ -n "$FAILED" ]; then echo "CI_FAILED:$FAILED"; exit 0; fi
  if [ "$TOTAL" -gt "0" ] && [ "$SUCCESS" -eq "$TOTAL" ]; then echo "CI_PASSED"; exit 0; fi
  sleep 30
done
```

**6.3 — Bot review 監聽（run_in_background: true）**

```bash
REPO=<repo>; PR=<pr-number>
while true; do
  COUNT=$(gh api repos/$REPO/pulls/$PR/comments \
    --jq '[.[] | select(.user.login | test("bot|gemini|copilot|robot"; "i"))] | length')
  if [ "$COUNT" -gt "0" ]; then echo "BOT_FOUND"; exit 0; fi
  sleep 30
done
```

**6.4 — 用 Monitor tool 訂閱兩個 process 輸出**

**6.5 — 根據訊號處理**

| 訊號 | 動作 |
|---|---|
| `CI_PASSED` | 通知使用者：CI 全部通過 |
| `CI_FAILED:<context>` | 通知使用者，取得 build log 後回報錯誤細節 |
| `BOT_FOUND` | 立即 invoke `Skill("pr-review", "<pr-number>")` |
