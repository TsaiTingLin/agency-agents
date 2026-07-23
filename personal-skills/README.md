# Personal Skills

Ship faster without the busywork. Built on [agency-agents](../README.md), Personal Skills automates your full development cycle — Jira ticket → implementation → code review → commit → PR → CI → release notes — all triggered by natural language in Claude Code and Codex.

---

## Quick Start — New Machine Setup

### Prerequisites

**Tools** — install once before running the setup scripts:

| Tool | What it's for | Install |
|---|---|---|
| `gh` | GitHub CLI — used by PR and release workflows | `brew install gh && gh auth login` |
| `node` / `npm` | Required to run OpenSpec | `brew install node` |
| `python3` | Required by sync scripts | `brew install python3` |
| OpenSpec | Spec-driven development CLI — used by `opsx:*` skills | See [docs](https://kaochenlong.com/openspec) |
| Superpowers | Skill framework for Claude Code — used by brainstorming, review, and planning skills | See [docs](https://kaochenlong.com/ai-superpowers-skills) |

**MCP connections** — only needed for the skills that use them. Enable at [claude.ai → Settings → Connectors](https://claude.ai/new#settings/customize-connectors):

| MCP | Used by | Setup |
|---|---|---|
| Atlassian / Jira | `jira-ticket`, `new-jira-ticket`, `pr-review`, `write-pr`, `quality-gate` | [Enable in Connectors](https://claude.ai/new#settings/customize-connectors) |
| Figma | `jira-ticket` (when ticket contains Figma links) | [Enable in Connectors](https://claude.ai/new#settings/customize-connectors) |
| Jenkins | `jenkins-build` | Custom MCP — server lives in `personal-skills/tools/jenkins-monitor/`. Auto-configured by `sync-skills.sh`. Requires `JENKINS_URL`, `JENKINS_USER`, `JENKINS_TOKEN` in `~/.zshrc`. |

### Setup

```bash
# 1. Clone the repo
git clone git@github.com:<your-username>/agency-agents.git ~/agency-agents
cd ~/agency-agents

# 2. Copy local config and fill in your values
cp personal-skills/config/local.env.example personal-skills/config/local.env
# Edit local.env with your project-specific values (see local.env.example for descriptions)

# 3. Install agents into the target tool
./scripts/install.sh --tool claude-code   # Claude Code
./scripts/install.sh --tool codex         # Codex

# 4. Preview what sync will do (dry run)
./scripts/sync-skills.sh --to claude --dry-run   # Claude Code
./scripts/sync-skills.sh --to codex --dry-run    # Codex
```

The dry-run output has three sections:
- `[OK]` / `[!!]` — preflight: checks tools, MCP connections, and env vars. `[!!]` items are warnings for optional runtime dependencies not yet configured — install still succeeds. Only configure what the skills you actually use require; ignore `[!!]` for skills you don't use.
- `copy ...` — skills and tools that will be installed
- `dry-run ...` — config files (`CLAUDE.md`, `settings.json`) that will be merged

```bash
# 5. Sync skills, tools, and config
./scripts/sync-skills.sh --to claude --replace   # Claude Code
./scripts/sync-skills.sh --to codex --replace    # Codex
```

### 6. Add to `~/.zshrc`

Add the following to `~/.zshrc`:

```bash
# Claude Code / Codex CLI session cleanup (both tools share the same
# TERM_SESSION_ID within one terminal tab, so one trap covers both)
trap '[[ -n "$TERM_SESSION_ID" ]] && rm -rf "$HOME/.claude/review/$TERM_SESSION_ID" "$HOME/.codex/review/$TERM_SESSION_ID" 2>/dev/null' EXIT

# Jenkins MCP credentials (only needed for /jenkins-build)
export JENKINS_URL="https://your-jenkins.com"
export JENKINS_USER="your-username"
export JENKINS_TOKEN="your-token"
```

Then run `source ~/.zshrc` to apply, or just open a new terminal.

That's it — you're all set. Have fun! 🚀

---

## Reference

### Layout

```text
agency-agents/
├── engineering/        ← agent source files (engineering agents)
├── specialized/        ← agent source files (specialized agents)
├── scripts/
│   ├── install.sh          ← installs agents into target tool
│   └── sync-skills.sh      ← installs skills, tools, and config
└── personal-skills/
    ├── commands/       ← skill files
    │                     Claude Code: ~/.claude/commands/
    │                     Codex:       ~/.codex/skills/claude-command-*/
    ├── config/
    │   ├── CLAUDE.md           ← merged into ~/.claude/CLAUDE.md (Claude Code only)
    │   ├── settings.json       ← merged into ~/.claude/settings.json (Claude Code only)
    │   ├── local.env.example   ← copy to local.env and fill in values
    │   └── local.env           ← gitignored, machine-local
    └── tools/          ← helper scripts
                          Claude Code: ~/.claude/tools/
                          Codex:       ~/.codex/tools/
```

### Variables

Skills and agents use placeholders that are substituted at install/sync time. This keeps the repo files project-agnostic — no hardcoded absolute paths — so the same files work across machines and projects just by setting `local.env`.

| Variable | Source | Substituted in | Description |
|---|---|---|---|
| `{{HOME}}` | `$HOME` (shell) | skills, agents | User home directory — no config needed |
| `{{PROJECT_REPO}}` | `local.env` → `PROJECT_REPO` | skills, CLAUDE.md | Absolute path to your primary project repo |
| `{{PROJECT_CONVENTIONS_AGENT}}` | `local.env` → `PROJECT_CONVENTIONS_AGENT` | skills | Filename of the project conventions agent (must exist in `~/.claude/agents/`). Defaults to `engineering-project-example-conventions.md` — rename and edit it for your project. |
| `{{JIRA_PROJECT_KEY}}` | `local.env` → `JIRA_PROJECT_KEY` | Jira skills | Jira project key (e.g. `PROJ`) — the prefix before the ticket number, used in JQL queries |
| `{{JIRA_BASE_URL}}` | `local.env` → `JIRA_BASE_URL` | Jira skills | Jira instance URL (e.g. `https://yourcompany.atlassian.net`) |
| `{{JIRA_ASSIGNEE_EMAIL}}` | `local.env` → `JIRA_ASSIGNEE_EMAIL` | Jira skills | Email used for Jira assignee lookup |
| `{{JIRA_WORKSPACE_ID}}` | `local.env` → `JIRA_WORKSPACE_ID` | Jira skills | Jira cloud workspace ID for Atlassian MCP `cloudId` param |
| `{{PR_REVIEWERS}}` | `local.env` → `PR_REVIEWERS` | `write-pr` | Comma-separated GitHub reviewer list for `gh pr create` |
| `{{JENKINS_JOB_PREFIX}}` | `local.env` → `JENKINS_JOB_PREFIX` | `jenkins-build` | CI job name prefix (e.g. `MyCompany-Android-CI-Develop`) |

`local.env` is gitignored and never committed. If a variable is left unset, the placeholder stays as-is in the installed file — a visible signal that setup is incomplete.

### Agents

Agents are persona/behavior files that Claude loads to take on a specialized role — e.g. code reviewer, architect, mobile app builder. They are separate from skills: a skill is a workflow (step-by-step instructions), an agent is a role (expertise + constraints).

Source files live in `agency-agents/engineering/`, `agency-agents/specialized/`, etc. `install.sh` copies them into `~/.claude/agents/` (Claude Code) or the equivalent for other tools, applying variable substitution.

Skills that need specialized behavior read the relevant agent file at runtime — for example, `/pre-commit-review` reads `engineering-code-reviewer.md` and `engineering-git-workflow-master.md` at Step 1 before doing anything.

The following agents are specific to this skill workflow:

| Agent | Location | Description | Used by |
|---|---|---|---|
| Quality Gate Mentor | `engineering/engineering-quality-gate-mentor.md` | Adversarial quality gate for skill execution — default stance is BLOCK; PASS requires evidence. | `/quality-gate` |
| Project Conventions Agent | `{{PROJECT_CONVENTIONS_AGENT}}` (set in `local.env`) | Project-specific coding conventions. Loaded automatically for project-related tasks. Start from `engineering-project-example-conventions.md` and customise for your project. | `/jira-ticket`, `/new-feature`, `/pre-commit-review` |

### Skills

Skills install to `~/.claude/commands/` (Claude Code) or `~/.codex/skills/` (Codex). Invoke with `/skill-name`.

The skills below are on `main`. Project-specific branches may add additional skills not listed here.

You don't need to type the slash command directly — just describe what you want in natural language and Claude will trigger the right skill automatically. Claude decides based on the `Use when` clause in each skill's `description` frontmatter. If a phrase doesn't work, add it to the `Use when` clause in `personal-skills/commands/<skill>.md`.

**Feature development**

| Skill | Description | 何時觸發 |
|---|---|---|
| `/new-feature` | Full flow from requirement to commit — brainstorm, plan, implement, review, commit. No Jira required. | 「我要做一個新功能」、任何新功能 / bug fix / 重構任務 |
| `/new-jira-ticket` | Full flow from requirement to Jira ticket — brainstorm, create ticket, optionally kick off implementation. Requires Jira env vars. | 「幫我開一個 Jira ticket」 |
| `/jira-ticket` | Read Jira ticket, implement via OpenSpec, then commit. Requires Jira env vars and OpenSpec. | 「幫我做 PROJ-1234」（提供 ticket 編號）|
| `/pre-commit-review` | Review staged changes, auto-fix issues, run tests, mentor-check, then commit. | 「幫我 commit」、「review 一下準備 commit」 |
| `/write-pr` | Generate PR description from Jira tickets and open GitHub PR. | 「幫我開 PR」、「寫 PR description」 |
| `/pr-review` | Address GitHub PR review comments, fix code, commit, then reply to reviewers. | 「PR #123 有 review comments 要處理」 |
| `/jenkins-build` | Trigger Jenkins CI build, monitor result, fix failures. Requires Jenkins MCP. Job must have `BranchName` (String) and `ProductFlavor` (Choice: Alpha/Beta) params; job naming convention and success detection are org-specific — adapt `commands/jenkins-build.md` if your setup differs. | 「build develop alpha」 |
| `/new-release-note` | Generate release notes from Jira fixVersion, create git tag, and publish GitHub release. | 「幫我做 release note」、「我想要建立 release note」 |

**Personal productivity**

| Skill | Description | 何時觸發 |
|---|---|---|
| `/setup-gmail-slack-digest` | Categorize unread Gmail and send a digest to your Slack self-DM. **Codex:** the skill checks the Gmail and Slack plugins; when prompted, manually approve and connect them before it creates the Codex automation. **Claude Code:** the skill runs the Slack plugin install command and guides setup of the `workspace-gmail` MCP (`google_workspace_mcp`). | 「幫我設定 Gmail 未讀整理」、「把 Gmail 未讀信整理到 Slack」 |

**Quality gate**

| Skill | Description | 何時觸發 |
|---|---|---|
| `/quality-gate` | Mentor check — verifies plans and commits at key checkpoints; supports both Jira and no-Jira modes | 自動在 skill 執行關鍵節點觸發 |

**Reflection**

| Skill | Description | 何時觸發 |
|---|---|---|
| `/reflect` | Record an issue or lesson into session memory | 「檢討一下」、「記錄一下」、「這個要記起來」 |
| `/retrospective` | Review session issues and propose skill/agent updates | 「總結檢討」、「看一下問題」、「有什麼要改的」 |
