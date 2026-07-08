---
description: "Review staged changes, auto-fix issues, and commit. Use when local changes are ready for commit."
argument-hint: "[ticket number or plan path (optional)]"
allowed-tools: ["Bash", "Read", "Edit", "Write", "Glob", "Grep"]
---

# Pre-Commit Review & Commit

Review all local changes against coding standards, fix issues, then commit.

**Ticket / Plan (optional):** "$ARGUMENTS"

---

## Step 1 — Load standards

Read both agent files before doing anything else:
- `{{HOME}}/.claude/agents/engineering-code-reviewer.md`
- `{{HOME}}/.claude/agents/engineering-git-workflow-master.md`

Check if we're in the configured project repo:
```bash
git rev-parse --show-toplevel
```

If the path starts with `{{PROJECT_REPO}}`, also read:
- `{{HOME}}/.claude/agents/{{PROJECT_CONVENTIONS_AGENT}}`

Keep all rules in mind throughout this workflow.

---

## Your Role — 縝密執行者

- 每一步做完整，不跳過、不猜測
- Review 時看到問題，**主動說出來**，不是等使用者發現
- 如果你認為某個修正有問題或引入新 bug，說出來，不是默默照改
- 有疑問先問再動，不是猜測後執行

---

## Step 2 — Collect local changes

```bash
git branch --show-current
git status
git diff HEAD
git diff --cached
```

若沒有任何變更，停止並告知使用者。

---

## Step 3 — Review the changes

Apply all rules from the agent files loaded in Step 1. Present findings:

```
## Pre-Commit Review

### 🔴 Blockers
- [file:line] description

### 🟡 Suggestions
- [file:line] description

### 💭 Nits
- [file:line] description

### ✅ Looks good
- summary of what's correct
```

**Immediately proceed to Step 4 — do NOT ask for confirmation here.**

---

## Step 4 — Fix issues

Fix **all 🔴 Blockers** and **🟡 Suggestions** automatically without asking. Fix **💭 Nits** too.

Show a summary of changes made:
```
## Fixes Applied
- [file]: what was changed
```

---

## Step 5 — Run tests

**Skip this step entirely** if the user has said "no test", "skip test", "不要跑 test", or any equivalent at any point in the current session.

If `{{PROJECT_CONVENTIONS_AGENT}}` was loaded in Step 1, check if it defines pre-commit test commands. If yes, run them.

**Before running tests — verify staging area matches working tree:**
```bash
git diff --name-only
```
If this outputs any files, **stop**. Stage or discard the differences before running tests — otherwise tests prove the working tree, not what will be committed.

If tests fail: report and stop. Do NOT suggest committing until resolved.

---

## Step 5.5 — mentor-check-commit (MANDATORY — do NOT skip)

Determine arguments:
- **Ticket**: from `$ARGUMENTS` if it looks like a ticket number, otherwise from branch name, otherwise `none`
- **Plan path**: from `$ARGUMENTS` if it looks like a file path, otherwise `none`

```
/quality-gate mentor-check-commit <ticket-or-none> <plan-path-or-none>
```

Wait for **MENTOR-CHECK-COMMIT RESULT: PASS** before continuing.
If BLOCK: fix and re-run. Do NOT proceed to Step 6 until it passes.

---

## Step 6 — Stage all changes and confirm commit

Stage all relevant files:
```bash
git add <all relevant files>
git status
git diff --cached --stat
```

Propose a commit message following the format in `engineering-git-workflow-master.md`. If a ticket number is available, include it as prefix; otherwise omit.

Then ask:
> "Ready to commit with the message above. Say **yes** to commit, or tell me to adjust the message."

**Do NOT commit until the user says yes.**

---

## Step 7 — Commit

```bash
git commit -m "$(cat <<'EOF'
<commit message>

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>
EOF
)"
git log --oneline -1
```
