---
name: jenkins-build
description: Full Jenkins build workflow — confirm job, update parameters, trigger build, monitor result, fix failures, report version. Use when user says "build [branch] alpha/beta" or wants to trigger a Jenkins CI build.
---

# Jenkins Build Workflow

Follow these steps in order every time the user requests a Jenkins build.

## Step 1 — Identify Job

Call `mcp__jenkins-monitor__list_jobs` and filter for CI jobs.

Map the branch name to the target job name:
- Strip common prefixes (`develop-root-`, `develop-`, `feature/`) from the branch name
- Title-case each word with hyphens → e.g. `feature/bolus-calculator` → `Bolus-Calculator`
- Target job name: `{{JENKINS_JOB_PREFIX}}-<suffix>`

### Step 1a — Confirm Job

Present choices to the user, marking the target job as recommended:

> 請選擇要使用的 job：
> 1. `{{JENKINS_JOB_PREFIX}}-<target>` ← 建議（若存在）
> 2. `{{JENKINS_JOB_PREFIX}}-Foo`
> 3. `{{JENKINS_JOB_PREFIX}}-Bar`
> …（列出所有符合 prefix 的 jobs）

**Do NOT proceed until the user selects.**

### Step 1b — Confirm Naming

Compare the selected job name suffix with the target suffix. If they differ:

> 是否將 job 改名？
> 1. 改為 `{{JENKINS_JOB_PREFIX}}-<target>`（建議）
> 2. 保持現有名稱 `<selected-job>`

If the user chooses to rename, call `mcp__jenkins-monitor__rename_job`.

## Step 2 — Update Parameters

Always call `mcp__jenkins-monitor__update_job_parameter` for both parameters:
- `BranchName` → the branch the user requested
- `ProductFlavor` → `Alpha` or `Beta` as requested

## Step 3 — Trigger Build

Call `mcp__jenkins-monitor__get_build_status` (no build_number) to record the current latest build number as **N**.

Then call `mcp__jenkins-monitor__trigger_build` with the job name and branch.

## Step 4 — Monitor Build

Poll `mcp__jenkins-monitor__get_build_status` with **`build_number: N+1`** every 30 seconds.
Show the user a progress update each time you poll.

**Never call without `build_number` during monitoring** — it returns the last completed build.

**Queue wait is normal** — if `N+1` returns 404, the build is still queued. Keep polling silently.

## Step 5 — On Success

⚠️ **Do NOT trust `result: "SUCCESS"` alone.** Some pipelines run scripts after the build that exit 0 even when compilation failed.

Call `mcp__jenkins-monitor__get_build_log` (max_lines: 300) and check:

**Failure indicators (any → treat as Step 6):**
- `BUILD FAILED`
- `FAILED` on any compile/assemble task

**Positive confirmation (must be present):**
- Evidence that a build artifact was produced (APK path, artifact upload line, etc.)

If checks pass, report to the user:
- Build number, branch, ProductFlavor, version from `display_name`

## Step 6 — On Failure

### 6.1 — Load standards and initialize session

Read the following agent files:
- `{{HOME}}/.claude/agents/engineering-code-reviewer.md`
- `{{HOME}}/.claude/agents/engineering-minimal-change-engineer.md`

Then check the repo root:
```bash
git rev-parse --show-toplevel
```
If the path starts with `{{PROJECT_REPO}}`, also read:
- `{{HOME}}/.claude/agents/{{PROJECT_CONVENTIONS_AGENT}}`

Initialize session:
```bash
python3 ~/.claude/tools/mentor_memory.py init
```

### 6.2 — Analyze and fix

1. Call `mcp__jenkins-monitor__get_build_log` (max_lines: 300) and `mcp__jenkins-monitor__get_failed_tests`
2. Analyze the root cause from the logs
3. Locate the relevant code in `{{PROJECT_REPO}}`
4. Fix the code

### 6.3 — Commit and branch

After fixes are complete, ask:
> "修復完成。要直接 push 到 `<build-branch>`，還是開新分支 + PR？"

- **直接 push**：invoke `/pre-commit-review`，commit 後 push，re-trigger build → return to Step 6
- **開新分支 + PR**：checkout new branch, invoke `/pre-commit-review`，invoke `/write-pr`，re-trigger build → return to Step 6
