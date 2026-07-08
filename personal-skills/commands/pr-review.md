---
description: "Read GitHub PR comments, fix code, commit, then auto-reply to each reviewer. Use when the user mentions a PR number and wants to address review comments from GitHub."
argument-hint: "<PR 編號，例：123>"
---

Address review comments on GitHub PR $ARGUMENTS and apply the necessary code fixes.

## Instructions

If no PR number is provided in $ARGUMENTS, ask the user: "Please provide the PR number."

---

### Step 1 — Load team standards

Read the following agent files:
- `{{HOME}}/.claude/agents/engineering-code-reviewer.md`
- `{{HOME}}/.claude/agents/engineering-minimal-change-engineer.md`

Then check the repo root:
```bash
git rev-parse --show-toplevel
```
If the path starts with `{{PROJECT_REPO}}`, also read:
- `{{HOME}}/.claude/agents/{{PROJECT_CONVENTIONS_AGENT}}`

Keep all rules in mind when planning and implementing fixes.

---

## Your Role — 縝密執行者

- 每一步做完整，不跳過、不猜測
- 看到 reviewer 的建議，**先獨立驗證**，再決定是否採納
- 如果你認為某個 fix 方向有問題，說出來，不是默默照做
- 有疑問先問再動，不是猜測後執行

---

### Step 2 — Fetch PR review data

```bash
REPO=$(gh repo view --json nameWithOwner -q '.nameWithOwner')
ME=$(gh api user -q '.login')

gh pr view $ARGUMENTS --json number,title,headRefName,baseRefName,state,mergeable,mergeStateStatus,author

gh api repos/$REPO/pulls/$ARGUMENTS/comments --paginate \
  | jq '.[] | {id, author: .user.login, path, line, in_reply_to_id, body: .body[:400]}'

gh api repos/$REPO/pulls/$ARGUMENTS/reviews --paginate \
  | jq '.[] | {id, author: .user.login, state, body: .body[:400]}'

gh api repos/$REPO/issues/$ARGUMENTS/comments --paginate \
  | jq '.[] | {id, author: .user.login, body: .body[:400]}'

gh pr diff $ARGUMENTS
```

---

### Step 2.1 — Determine PR mode

- `author.login == ME` → **My PR mode**: proceed through all steps including fix, commit, and reply
- `author.login != ME` → **Others' PR mode**: do code review only (Steps 3–5), then stop

---

### Step 2.2 — Check merge conflict status

If `mergeable == "CONFLICTING"` or `mergeStateStatus == "DIRTY"`:
- Report immediately and identify conflicting files
- Then continue the review normally

---

### Step 2.5 — Check for pre-staged changes

```bash
git diff --cached --stat
```

If pre-staged changes exist, ask the user how to handle them before proceeding.

---

### Step 3 — Understand existing review status

Parse GitHub data from Step 2:
- For each reviewer comment: what was flagged, and is it still open or already addressed?

---

### Step 4 — Independent code review (MANDATORY)

Read the **full current file** for every changed file:
```bash
git fetch origin <headRefName>
git show origin/<headRefName>:path/to/changed/file
```

Apply the full checklist from `engineering-code-reviewer.md` independently. If `{{PROJECT_CONVENTIONS_AGENT}}` was loaded, also apply its coding standards.

**MANDATORY — Call site search:**

For every class or function whose constructor signature or public API changed, run:
```bash
git grep -n "<ClassName>\|<functionName>" origin/<headRefName>
```

Check every result for production or test callers not updated in the diff.

---

### Step 5 — Combine and present findings

```
## PR #[number] Review Summary

### 📝 PR 目標與調整重點
2-3 句說明這個 PR 要解決什麼，接著條列主要變動。

### 📋 Existing Review Comments
For each GitHub comment — status (✅ addressed / ⚠️ still open) and brief note.

### 🔍 Independent Review Findings
Issues found that are NOT already covered by reviewer comments with sound author replies.
Use 🔴 / 🟡 / 💭 priority markers.
```

- **Others' PR mode** → Stop here.
- **My PR mode** → Ask: "Does this look right? Say **yes** to proceed with fixes."

---

### Step 6 — Implement the fixes
*(My PR mode only)*

---

### Step 6.1 — Update existing spec (if applicable)

Check whether there is an existing spec file for this change in `openspec/changes/`. If one exists, update it to reflect the fixes.

---

### Step 6.5 — Present disposition table and confirm before committing

```
## 處置確認表 — PR #[number]

| # | 檔案 | Comment 摘要 | 處置 | 預計 reply |
|---|------|-------------|------|-----------|
| 1 | `Foo.kt:42` | 問題描述 | ✅ 已修 / ⏭️ 不改 | 已調整 / 保留原本寫法，原因：... |
```

⛔ **Do NOT commit until the user explicitly confirms this table.**

---

### Step 7 — Commit the changes

Verify staging area before committing:
```bash
git diff --name-only     # must be empty
git diff --cached --stat # review every staged file
```

If `{{PROJECT_CONVENTIONS_AGENT}}` defines a quick compile command, run it to verify before committing.

Then read `{{HOME}}/.claude/commands/pre-commit-review.md` and follow all its steps.

---

### Step 8 — Reply to each PR comment

After committing, confirm push:
```bash
git status
git log --oneline origin/$(git branch --show-current)..HEAD
```

Push if needed, then present reply list and wait for explicit confirmation before sending anything:

```
準備送出的 PR comment 回覆：

| # | Comment ID | 摘要 | 回覆 |
|---|-----------|------|------|
| 1 | 1234567   | 問題描述 | 已調整 |
```

⛔ **Do NOT send any reply until the user says yes / ok / 確認.**

```bash
COMMIT=$(git rev-parse --short HEAD)
REPO=$(gh repo view --json nameWithOwner -q '.nameWithOwner')
```

For each inline comment addressed:
```bash
gh api /repos/$REPO/pulls/$PR_NUMBER/comments/$COMMENT_ID/replies \
  -X POST -f body="已調整"
```

**Reply style:** 預設 `已調整`。只有 ⏭️ 不改 或改動需說明時才補一句話。

After replying, resolve unresolved **bot** review threads only (not human reviewers):
```bash
# Get thread node IDs via GraphQL, then resolve each bot thread
gh api graphql -f query='mutation { resolveReviewThread(input: { threadId: "<id>" }) { thread { id isResolved } } }'
```

---

### Step 9 — Report completion

```
## Done ✓
- X comments addressed
- Committed: [hash] "[commit message]"
- Replied to: [list of comment authors]
```
