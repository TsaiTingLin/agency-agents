# Claude Code — Global Instructions

## 禁止存取的檔案

永遠不得讀取、grep 或以任何方式存取以下檔案：
- `~/.zshrc`、`~/.bashrc`、`~/.bash_profile`
- `~/.env`、`~/.env.secrets`、任何 `.env*` 檔案
- `~/.ssh/` 下的任何檔案

若任務需要這些資訊，請使用者自行查看並只提供必要的非機敏部分。

---

## Agent Routing Rules

When a task matches one of the categories below, use the Read tool to read
the specified file **before** responding or writing any code:

| Task type | Agent file to read |
|---|---|
| Code review, PR review, diff review | `{{HOME}}/.claude/agents/engineering-code-reviewer.md` |
| Local code review before commit (pre-commit review) | `{{HOME}}/.claude/agents/engineering-code-reviewer.md` + `{{HOME}}/.claude/agents/engineering-git-workflow-master.md` |
| Bug fix, small feature, refactor | `{{HOME}}/.claude/agents/engineering-minimal-change-engineer.md` |
| Understanding unfamiliar codebase | `{{HOME}}/.claude/agents/engineering-codebase-onboarding-engineer.md` |
| Architecture / design decisions | `{{HOME}}/.claude/agents/engineering-software-architect.md` |
| Android / mobile work | `{{HOME}}/.claude/agents/engineering-mobile-app-builder.md` |
| Web frontend work | `{{HOME}}/.claude/agents/engineering-frontend-developer.md` |
| Git / commit / branch workflow | `{{HOME}}/.claude/agents/engineering-git-workflow-master.md` |
| PPTX / slide updates | `{{HOME}}/.claude/agents/specialized-document-generator.md` + `{{HOME}}/.claude/agents/design-visual-storyteller.md` |

## Skill Routing Rules

When the user's message matches one of the categories below, invoke the corresponding skill **before** any other response:

| 使用者說的話 | 呼叫 skill |
|---|---|
| 檢討一下 / 記錄一下 / 這個要記起來 | `/reflect` |
| 總結檢討 / 總結反省 / 看一下問題 / 有什麼要改的 | `/retrospective` |

## Skill Priority

When a user-defined skill (`~/.claude/commands/`) and an official plugin skill overlap in name or purpose, **always prefer the user-defined skill**. Plugin skills (namespaced with `plugin:`) are only used when no equivalent user-defined skill exists.

## Skill Execution — Step Awareness

**At every skill step, before taking any action, confirm:**

1. **Which skill am I in?** (e.g. `jira-ticket`, `pre-commit-review`, `write-pr`)
2. **Which step am I on?** (e.g. Step 6 of `jira-ticket`)
3. **Is there a parent skill?** If this skill was invoked as a sub-step (e.g. `pre-commit-review` called from `jira-ticket` Step 6), the parent skill's next step must execute after this skill completes — not arbitrary actions.

**After completing any skill (or sub-skill):**
- If inside a parent skill → proceed to the parent's next step
- If unsure → stop and ask: 「接下來要做什麼？」
- Never improvise next actions outside the skill's defined steps

**External actions (gh pr create, git push, send message) without a skill:**
- Always blocked — find the appropriate skill first (`/write-pr`, etc.)

## Communication

Always respond to the user in **Traditional Chinese (繁體中文)**.

## Coding Conventions

- **Code comments must always be written in English**, regardless of the conversation language. This applies to all inline comments, docstrings, and block comments in any source file (.kt, .swift, .py, .ts, etc.).

## Continuous Improvement — Skill and Agent Updates

**When the user questions or challenges my approach and a conclusion is reached**, immediately evaluate:

1. Is this conclusion a **general principle** (not one-off) that would improve future work?
2. Which file owns this principle?
   - Workflow steps / process gates → skill file in `~/.claude/commands/`
   - Language/framework coding conventions → `~/agency-agents/<category>/` agent file
   - Project-specific patterns → this CLAUDE.md or memory
3. If yes → propose the update, make the change, and sync agent files if needed.

**Do not wait for the user to ask "should we update the skill/agent?"** — proactively surface it at the end of the discussion when a conclusion is clear.

## Agent File Editing Rules

Agent files in `~/.claude/agents/` are managed by the `~/agency-agents` repository.

- **Never edit `~/.claude/agents/*.md` directly** — changes will be overwritten on the next install.
- Edit the source files in `~/agency-agents/<category>/` instead (e.g. `engineering/`, `specialized/`).
- Skills in `~/.claude/commands/` are **not** managed by agency-agents — edit them directly.
- After editing, sync to Claude Code by running:
  ```bash
  cd ~/agency-agents && ./scripts/install.sh --tool claude-code
  ```
- **Do NOT commit or push** unless the user explicitly asks.
- When asked to commit/push, use:
  ```bash
  cd ~/agency-agents
  git add <changed files> && git commit -m "chore: ..."
  git push origin main
  ```
- Remote: `git@github.com:TsaiTingLin/agency-agents.git`

## Project-specific Rules

<!-- Add per-project rules below. Example:

### MyProject (`{{PROJECT_REPO}}`)

For ANY code-related task in this project, read
`{{HOME}}/.claude/agents/{{PROJECT_CONVENTIONS_AGENT}}` before writing or
reviewing code.
-->
