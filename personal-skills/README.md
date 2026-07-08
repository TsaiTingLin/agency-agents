# Personal Skills

This directory is the source of truth for personal workflow commands that should
be installed into multiple AI tools.

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

# 5. Sync skills, tools, and config
./scripts/sync-skills.sh --to claude --replace   # Claude Code
./scripts/sync-skills.sh --to codex --replace    # Codex
```

After sync completes, add the following to `~/.zshrc` if not already present:

```bash
# Claude Code session cleanup
trap '[[ -n "$TERM_SESSION_ID" ]] && rm -rf "$HOME/.claude/review/$TERM_SESSION_ID" 2>/dev/null' EXIT
```

If you use the `/jenkins-build` skill, also add Jenkins credentials:

```bash
# Jenkins MCP credentials (only needed for /jenkins-build)
export JENKINS_URL="https://your-jenkins.com"
export JENKINS_USER="your-username"
export JENKINS_TOKEN="your-token"
```

The dry-run output has three sections:
- `[OK]` / `[!!]` — preflight: checks tools, MCP connections, and env vars. `[!!]` items are warnings for optional runtime dependencies not yet configured — install still succeeds. Only configure what the skills you actually use require; ignore `[!!]` for skills you don't use.
- `copy ...` — skills and tools that will be installed
- `dry-run ...` — config files (`CLAUDE.md`, `settings.json`) that will be merged

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

### Branch Strategy

| Branch | Purpose |
|---|---|
| `main` | Generic — works for any project. `local.env.example` contains commented-out examples only. Clone this to start fresh. |
| project branches | Pre-configured for a specific project — `local.env.example` has values pre-filled and `config/CLAUDE.md` includes project-specific rules. Not pushed to remote (may contain private config). |

Clone `main` and fill in `local.env` to set up for your project. Project-specific branches exist only locally.

### Variables

Skills and agents use placeholders that are substituted at install/sync time. This keeps the repo files project-agnostic — no hardcoded absolute paths — so the same files work across machines and projects just by setting `local.env`.

| Variable | Source | Substituted in | Description |
|---|---|---|---|
| `{{HOME}}` | `$HOME` (shell) | skills, agents | User home directory — no config needed |
| `{{PROJECT_REPO}}` | `local.env` → `PROJECT_REPO` | skills, CLAUDE.md | Absolute path to your primary project repo |
| `{{PROJECT_CONVENTIONS_AGENT}}` | `local.env` → `PROJECT_CONVENTIONS_AGENT` | skills | Filename of the project conventions agent (must exist in `~/.claude/agents/`) |
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

### Skills

Skills install to `~/.claude/commands/` (Claude Code) or `~/.codex/skills/` (Codex). Invoke with `/skill-name`.

The skills below are on `main`. Project-specific branches may add additional skills not listed here.

**Feature development**

| Skill | Description |
|---|---|
| `/new-feature` | Full flow from requirement to commit — brainstorm, plan, implement, review, commit. No Jira required. |
| `/new-jira-ticket` | Full flow from requirement to Jira ticket — brainstorm, create ticket, optionally kick off implementation. Requires Jira env vars. |
| `/jira-ticket` | Read Jira ticket, implement via OpenSpec, then commit. Requires Jira env vars and OpenSpec. |
| `/pre-commit-review` | Review staged changes, auto-fix issues, run tests, mentor-check-commit, then commit. |
| `/write-pr` | Generate PR description from Jira tickets and open GitHub PR. |
| `/pr-review` | Address GitHub PR review comments, fix code, commit, then reply to reviewers. |
| `/jenkins-build` | Trigger Jenkins CI build, monitor result, fix failures. Requires Jenkins MCP. |

**Quality gate**

| Skill | Description |
|---|---|
| `/quality-gate` | Mentor check — verifies plans and commits at key checkpoints; supports both Jira and no-Jira modes |

**Reflection**

| Skill | Description |
|---|---|
| `/reflect` | Record an issue or lesson into session memory |
| `/retrospective` | Review session issues and propose skill/agent updates |

### Jenkins MCP Venv

`sync-skills.sh` creates `personal-skills/tools/jenkins-monitor/.venv` — an isolated Python environment for the Jenkins MCP server's dependencies. Claude Code's MCP config points at the Python binary inside this venv so the server can run without touching system Python.
