#!/usr/bin/env bash
# --- USAGE-START ---  (sentinel for usage(); do not remove)
# sync-skills.sh -- Sync repo-managed personal commands/skills to AI tools.
#
# Source of truth:
#   personal-skills/commands/**/*.md
#   personal-skills/tools/**/*
#
# Destinations:
#   Claude Code commands: ~/.claude/commands/**/*.md
#   Codex skills:        ~/.codex/skills/claude-command-*/SKILL.md
#   Helper tools:        ~/.claude/tools or ~/.codex/tools
#
# Usage:
#   ./scripts/sync-skills.sh --to claude
#   ./scripts/sync-skills.sh --to codex
#   ./scripts/sync-skills.sh --to all
#
# Options:
#   --to <claude|codex|all>  Destination tool(s). Default: all.
#   --source <dir>           Source commands dir. Default: personal-skills/commands.
#   --claude-dest <dir>      Claude commands dir. Default: ~/.claude/commands.
#   --codex-dest <dir>       Codex skills dir. Default: ~/.codex/skills.
#   --tools-source <dir>     Source helper tools dir. Default: personal-skills/tools.
#   --claude-tools <dir>     Claude helper tools dir. Default: ~/.claude/tools.
#   --codex-tools <dir>      Codex helper tools dir. Default: ~/.codex/tools.
#   --include <a,b>          Only sync command slugs, e.g. new-jira-ticket,opsx-propose.
#   --replace                Replace existing destination files/directories.
#   --no-preflight           Skip dependency checks.
#   --dry-run                Print the plan without writing.
#   --help                   Show this help.
# --- USAGE-END ---  (sentinel for usage(); do not remove)

set -euo pipefail

if [[ -t 1 && -z "${NO_COLOR:-}" && "${TERM:-}" != "dumb" ]]; then
  C_GREEN=$'\033[0;32m'
  C_YELLOW=$'\033[1;33m'
  C_RED=$'\033[0;31m'
  C_BOLD=$'\033[1m'
  C_RESET=$'\033[0m'
else
  C_GREEN=''; C_YELLOW=''; C_RED=''; C_BOLD=''; C_RESET=''
fi

ok()     { printf "${C_GREEN}[OK]${C_RESET}  %s\n" "$*"; }
warn()   { printf "${C_YELLOW}[!!]${C_RESET}  %s\n" "$*"; }
err()    { printf "${C_RED}[ERR]${C_RESET} %s\n" "$*" >&2; }
header() { printf "\n${C_BOLD}%s${C_RESET}\n" "$*"; }

usage() {
  sed -n '/^# --- USAGE-START ---/,/^# --- USAGE-END ---/p' "$0" \
    | sed -e '1d;$d' -e 's/^# \{0,1\}//'
  exit 0
}

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

TOOL="all"
SOURCE_DIR="$REPO_ROOT/personal-skills/commands"
TOOLS_SOURCE_DIR="$REPO_ROOT/personal-skills/tools"
CLAUDE_DEST="${CLAUDE_COMMANDS_DIR:-${HOME}/.claude/commands}"
CODEX_DEST="${CODEX_SKILLS_DIR:-${HOME}/.codex/skills}"
CLAUDE_TOOLS_DEST="${CLAUDE_TOOLS_DIR:-${HOME}/.claude/tools}"
CODEX_TOOLS_DEST="${CODEX_TOOLS_DIR:-${HOME}/.codex/tools}"
INCLUDE=""
REPLACE=false
DRY_RUN=false
PREFLIGHT=true

# Load machine-local variables (gitignored, never committed)
[[ -f "$REPO_ROOT/personal-skills/config/local.env" ]] \
  && source "$REPO_ROOT/personal-skills/config/local.env"

slugify() {
  printf '%s' "$1" | tr '[:upper:]' '[:lower:]' \
    | sed 's/[^a-z0-9]/-/g; s/--*/-/g; s/^-//; s/-$//'
}

toml_escape_like_yaml_string() {
  printf '%s' "$1" | perl -0pe '
    s/\\/\\\\/g;
    s/"/\\"/g;
    s/\n/\\n/g;
    s/\r/\\r/g;
    s/\t/\\t/g;
  '
}

get_field() {
  local field="$1" file="$2"
  [[ "$(head -1 "$file")" == "---" ]] || return 0
  awk -v f="$field" '
    /^---$/ { fm++; next }
    fm == 1 && $0 ~ "^" f ": " {
      sub("^" f ": ", "")
      gsub(/^"|"$/, "")
      print
      exit
    }
  ' "$file"
}

get_body() {
  local body
  if [[ "$(head -1 "$1")" != "---" ]]; then
    body="$(cat "$1")"
  else
    body="$(awk '
      BEGIN { fm=0 }
      /^---$/ { fm++; next }
      fm >= 2 { print }
    ' "$1")"
  fi
  if [[ "$TOOL" == "codex" || "$TOOL" == "all" ]]; then
    printf '%s' "$body" | sed \
      -e "s#${HOME}/.claude/tools#${HOME}/.codex/tools#g" \
      -e 's#~/.claude/tools#~/.codex/tools#g'
  else
    printf '%s' "$body"
  fi
}

command_relpath() {
  local file="$1"
  local rel="${file#$SOURCE_DIR/}"
  printf '%s' "$rel"
}

command_slug() {
  local rel="${1%.md}"
  slugify "$(printf '%s' "$rel" | tr '/' '-')"
}

selected() {
  local slug="$1"
  [[ -n "$INCLUDE" ]] || return 0
  case ",$INCLUDE," in
    *,"$slug",*) return 0 ;;
    *) return 1 ;;
  esac
}

has_codex_openspec() {
  [[ -f "${CODEX_DEST}/openspec-propose/SKILL.md" ]] \
    && [[ -f "${CODEX_DEST}/openspec-apply-change/SKILL.md" ]]
}

has_codex_superpowers() {
  [[ -e "${HOME}/.agents/skills/superpowers" ]] \
    || [[ -f "${HOME}/.codex/superpowers/skills/using-superpowers/SKILL.md" ]] \
    || [[ -f "${HOME}/.codex/.tmp/plugins/plugins/superpowers/skills/using-superpowers/SKILL.md" ]]
}

has_codex_jenkins_mcp() {
  [[ -f "${HOME}/.codex/config.toml" ]] && grep -q 'mcp_servers\.jenkins-monitor' "${HOME}/.codex/config.toml"
}

has_h2_android_repo() {
  [[ -d "${H2_ANDROID_REPO:-${HOME}/H2/Android-App/h2-android}" ]]
}

has_github_cli() {
  command -v gh >/dev/null 2>&1
}

has_jenkins_env() {
  [[ -n "${JENKINS_URL:-}" && -n "${JENKINS_USER:-}" && -n "${JENKINS_TOKEN:-}" ]]
}

has_codex_agents() {
  [[ -d "${HOME}/.codex/agents" ]]
}

has_claude_agents() {
  [[ -d "${HOME}/.claude/agents" ]]
}

has_claude_superpowers() {
  [[ -d "${HOME}/.claude/plugins/cache/claude-plugins-official/superpowers" ]]
}

has_claude_openspec() {
  [[ -f "${HOME}/.claude/skills/openspec-propose/SKILL.md" ]] \
    && [[ -f "${HOME}/.claude/skills/openspec-apply-change/SKILL.md" ]]
}

has_python() {
  command -v python3 >/dev/null 2>&1 || command -v python >/dev/null 2>&1
}

get_python() {
  command -v python3 2>/dev/null || command -v python 2>/dev/null
}

has_npm() {
  command -v npm >/dev/null 2>&1
}

has_openspec() {
  command -v openspec >/dev/null 2>&1
}

has_atlassian_mcp() {
  claude mcp get "claude.ai Atlassian" 2>/dev/null | grep -q "Connected"
}

has_figma_mcp() {
  claude mcp get "claude.ai Figma" 2>/dev/null | grep -q "Connected"
}

has_h2_project_repo_placeholder() {
  grep -rq "{{PROJECT_REPO}}" "$SOURCE_DIR" 2>/dev/null
}

has_h2_conventions_placeholder() {
  grep -rq "{{PROJECT_CONVENTIONS_AGENT}}" "$SOURCE_DIR" 2>/dev/null
}

run_preflight() {
  $PREFLIGHT || return 0

  case "$TOOL" in
    codex|all)
      if has_codex_openspec; then
        ok "Codex dependency: OpenSpec skills found"
      else
        warn "Codex dependency: OpenSpec skills not found in $CODEX_DEST"
        warn "      Install/sync OpenSpec skills before using opsx or Jira-ticket workflows."
      fi

      if has_codex_superpowers; then
        ok "Codex dependency: Superpowers found"
      else
        warn "Codex dependency: Superpowers not found"
        warn "      If Superpowers is installed at ~/.codex/superpowers/skills, expose it with:"
        warn "      mkdir -p ~/.agents/skills"
        warn "      ln -s ~/.codex/superpowers/skills ~/.agents/skills/superpowers"
      fi

      if has_codex_jenkins_mcp; then
        ok "Codex dependency: Jenkins MCP config found"
      else
        warn "Codex dependency: Jenkins MCP config not found in ~/.codex/config.toml"
        warn "      jenkins-monitor source is in this repo and will sync to ~/.codex/tools/jenkins-monitor."
        warn "      Register that local server in Codex MCP config before using Jenkins workflows."
      fi

      if has_codex_agents; then
        ok "Codex dependency: agency agents directory found"
      else
        warn "Codex dependency: ~/.codex/agents not found"
        warn "      Run ./scripts/install.sh --tool codex before workflows that read agency agent files."
      fi
      ;;
  esac

  case "$TOOL" in
    claude|all)
      if has_claude_openspec; then
        ok "Claude dependency: OpenSpec skills found"
      else
        warn "Claude dependency: OpenSpec skills not found in ~/.claude/skills"
        warn "      Install/sync OpenSpec skills before using opsx or Jira-ticket workflows."
      fi

      if has_claude_superpowers; then
        ok "Claude dependency: Superpowers plugin cache found"
      else
        warn "Claude dependency: Superpowers plugin cache not found"
        warn "      Commands that invoke superpowers workflows may need the Superpowers plugin installed."
      fi

      if has_claude_agents; then
        ok "Claude dependency: agency agents directory found"
      else
        warn "Claude dependency: ~/.claude/agents not found"
        warn "      Run ./scripts/install.sh --tool claude-code before workflows that read agency agent files."
      fi

      if has_python; then
        ok "Python found: $(get_python)"
      else
        err "No python3 or python found — merge-settings.py cannot run"
        exit 1
      fi

      if has_npm; then
        ok "npm found"
      else
        warn "npm not found — install with: brew install node"
        warn "      openspec requires npm: npm install -g @fission-ai/openspec@latest"
      fi

      if has_openspec; then
        ok "openspec found"
      else
        warn "openspec not found — install with: npm install -g @fission-ai/openspec@latest"
      fi

      if has_atlassian_mcp; then
        ok "Atlassian MCP connected"
      else
        warn "Atlassian MCP not connected — configure at claude.ai to use Jira workflows"
      fi

      if has_figma_mcp; then
        ok "Figma MCP connected"
      else
        warn "Figma MCP not connected — configure at claude.ai to use Figma workflows"
      fi

      if has_h2_project_repo_placeholder; then
        if [[ -n "${PROJECT_REPO:-}" ]]; then
          ok "PROJECT_REPO: $PROJECT_REPO"
        else
          warn "PROJECT_REPO not set — {{PROJECT_REPO}} in skills will not be replaced"
          warn "      Set it in personal-skills/config/local.env"
        fi
      fi

      if has_h2_conventions_placeholder; then
        if [[ -n "${PROJECT_CONVENTIONS_AGENT:-}" ]]; then
          ok "PROJECT_CONVENTIONS_AGENT: $PROJECT_CONVENTIONS_AGENT"
        else
          warn "PROJECT_CONVENTIONS_AGENT not set — {{PROJECT_CONVENTIONS_AGENT}} in skills will not be replaced"
          warn "      Set it in personal-skills/config/local.env"
        fi
      fi
      ;;
  esac

  if has_h2_android_repo; then
    ok "Local dependency: H2 Android repo found"
  else
    warn "Local dependency: H2 Android repo not found at ${H2_ANDROID_REPO:-${HOME}/H2/Android-App/h2-android}"
    warn "      Set H2_ANDROID_REPO or update command source paths if this repo lives elsewhere."
  fi

  if has_github_cli; then
    ok "Local dependency: GitHub CLI found"
  else
    warn "Local dependency: GitHub CLI 'gh' not found"
    warn "      PR and release workflows need gh installed and authenticated."
  fi

  if has_jenkins_env; then
    ok "Local dependency: Jenkins env vars found"
  else
    warn "Local dependency: Jenkins env vars not fully set"
    warn "      jenkins-monitor needs JENKINS_URL, JENKINS_USER, and JENKINS_TOKEN."
  fi

}

replace_path() {
  local path="$1"
  [[ -e "$path" || -L "$path" ]] || return 0
  if ! $REPLACE; then
    return 1
  fi
  if $DRY_RUN; then
    printf '  replace %s\n' "$path"
  else
    rm -rf "$path"
  fi
  return 0
}

copy_tree_file() {
  local src="$1" from_dir="$2" to_dir="$3" rel dest
  rel="${src#$from_dir/}"
  dest="$to_dir/$rel"

  if [[ -e "$dest" || -L "$dest" ]]; then
    replace_path "$dest" || { printf '  skip    tool %s (exists)\n' "$rel"; return 0; }
  fi

  if $DRY_RUN; then
    printf '  copy    tool %s -> %s\n' "$rel" "$dest"
  else
    mkdir -p "$(dirname "$dest")"
    cp "$src" "$dest"
  fi
}

sync_tools_to() {
  local dest="$1" file count=0
  [[ -d "$TOOLS_SOURCE_DIR" ]] || return 0
  while IFS= read -r file; do
    copy_tree_file "$file" "$TOOLS_SOURCE_DIR" "$dest"
    count=$((count + 1))
  done < <(find "$TOOLS_SOURCE_DIR" -type f | sort)
  ok "Processed $count helper tool file(s) -> $dest"
}

sync_claude_command() {
  local src="$1" rel dest
  rel="$(command_relpath "$src")"
  dest="$CLAUDE_DEST/$rel"

  if [[ -e "$dest" || -L "$dest" ]]; then
    replace_path "$dest" || { printf '  skip    claude %s (exists)\n' "$rel"; return 0; }
  fi

  if $DRY_RUN; then
    printf '  copy    claude %s -> %s\n' "$rel" "$dest"
  else
    mkdir -p "$(dirname "$dest")"
    # Pre-compute values; unset variables keep their {{...}} form as fallback
    local _project_repo="${PROJECT_REPO}"; [ -z "$_project_repo" ] && _project_repo='{{PROJECT_REPO}}'
    local _conventions="${PROJECT_CONVENTIONS_AGENT}"; [ -z "$_conventions" ] && _conventions='{{PROJECT_CONVENTIONS_AGENT}}'
    local _jira_key="${JIRA_PROJECT_KEY}"; [ -z "$_jira_key" ] && _jira_key='{{JIRA_PROJECT_KEY}}'
    local _jira_url="${JIRA_BASE_URL}"; [ -z "$_jira_url" ] && _jira_url='{{JIRA_BASE_URL}}'
    local _jira_email="${JIRA_ASSIGNEE_EMAIL}"; [ -z "$_jira_email" ] && _jira_email='{{JIRA_ASSIGNEE_EMAIL}}'
    local _jira_ws="${JIRA_WORKSPACE_ID}"; [ -z "$_jira_ws" ] && _jira_ws='{{JIRA_WORKSPACE_ID}}'
    local _jenkins="${JENKINS_JOB_PREFIX}"; [ -z "$_jenkins" ] && _jenkins='{{JENKINS_JOB_PREFIX}}'
    local _pr_reviewers="${PR_REVIEWERS}"; [ -z "$_pr_reviewers" ] && _pr_reviewers='{{PR_REVIEWERS}}'
    sed -e "s|{{HOME}}|$HOME|g" \
        -e "s|{{PROJECT_REPO}}|$_project_repo|g" \
        -e "s|{{PROJECT_CONVENTIONS_AGENT}}|$_conventions|g" \
        -e "s|{{JIRA_PROJECT_KEY}}|$_jira_key|g" \
        -e "s|{{JIRA_BASE_URL}}|$_jira_url|g" \
        -e "s|{{JIRA_ASSIGNEE_EMAIL}}|$_jira_email|g" \
        -e "s|{{JIRA_WORKSPACE_ID}}|$_jira_ws|g" \
        -e "s|{{JENKINS_JOB_PREFIX}}|$_jenkins|g" \
        -e "s|{{PR_REVIEWERS}}|$_pr_reviewers|g" \
        "$src" > "$dest"
  fi
}

write_codex_skill() {
  local src="$1" rel slug skill_dir skill_file title desc body
  rel="$(command_relpath "$src")"
  slug="$(command_slug "$rel")"
  skill_dir="$CODEX_DEST/$slug"
  skill_file="$skill_dir/SKILL.md"

  if [[ -e "$skill_dir" || -L "$skill_dir" ]]; then
    replace_path "$skill_dir" || { printf '  skip    codex %s (exists)\n' "$slug"; return 0; }
  fi

  title="$(get_field name "$src")"
  [[ -n "$title" ]] || title="/${rel%.md}"
  desc="$(get_field description "$src")"
  [[ -n "$desc" ]] || desc="Use this when the user asks for the Claude command /${rel%.md} workflow."
  body="$(get_body "$src")"

  if $DRY_RUN; then
    printf '  render  codex %s -> %s\n' "$rel" "$skill_file"
    return 0
  fi

  mkdir -p "$skill_dir"
  {
    printf '%s\n' '---'
    printf 'name: %s\n' "$slug"
    printf 'description: "%s"\n' "$(toml_escape_like_yaml_string "$desc")"
    printf '%s\n' '---'
    printf '\n'
    printf '# %s\n\n' "$title"
    printf 'This Codex skill is synced from the Claude command `%s`.\n\n' "$rel"
    printf '## Compatibility Notes\n\n'
    printf -- '- Treat the original Claude slash command `/%s` as this skill trigger.\n' "${rel%.md}"
    printf -- '- Treat `$ARGUMENTS` as the user-provided input after the command name.\n'
    printf -- '- If the source mentions Claude-specific tools such as `Agent`, `AskUserQuestion`, `TodoWrite`, `Read`, `Edit`, or `Write`, use the closest available Codex tool/workflow instead.\n'
    printf -- '- This sync includes local helper tools such as jenkins-monitor source, but MCP registration, URLs, tokens, and external auth are not configured by this script.\n\n'
    printf '%s\n' '## Source Command'
    printf '\n'
    printf '%s\n' "$body"
  } > "$skill_file"
}

sync_commands() {
  local file rel slug total=0
  [[ -d "$SOURCE_DIR" ]] || { err "Source commands dir not found: $SOURCE_DIR"; exit 1; }

  header "Personal Skill Sync"
  printf '  Source: %s\n' "$SOURCE_DIR"
  printf '  Target: %s\n' "$TOOL"
  $REPLACE && printf '  Existing: replace\n' || printf '  Existing: skip\n'
  $DRY_RUN && printf '  Dry run: yes\n'
  printf '\n'
  run_preflight
  printf '\n'

  while IFS= read -r file; do
    rel="$(command_relpath "$file")"
    slug="$(command_slug "$rel")"
    selected "$slug" || continue
    total=$((total + 1))
    case "$TOOL" in
      claude) sync_claude_command "$file" ;;
      codex) write_codex_skill "$file" ;;
      all)
        sync_claude_command "$file"
        write_codex_skill "$file"
        ;;
    esac
  done < <(find "$SOURCE_DIR" -type f -name '*.md' | sort)

  ok "Processed $total command(s)"

  case "$TOOL" in
    claude) sync_tools_to "$CLAUDE_TOOLS_DEST" ;;
    codex) sync_tools_to "$CODEX_TOOLS_DEST" ;;
    all)
      sync_tools_to "$CLAUDE_TOOLS_DEST"
      sync_tools_to "$CODEX_TOOLS_DEST"
      ;;
  esac

  # Post-sync: config merge, CLAUDE.md, Jenkins MCP (claude target only)
  case "$TOOL" in
    claude|all)
      local config_dir="$REPO_ROOT/personal-skills/config"
      local claude_dir="$HOME/.claude"

      # Merge settings.json
      if [[ -f "$config_dir/settings.json" ]]; then
        if $DRY_RUN; then
          printf '  dry-run merge-settings.py -> %s/settings.json\n' "$claude_dir"
        else
          "$(get_python)" "$REPO_ROOT/scripts/merge-settings.py" \
            --template "$config_dir/settings.json" \
            --target "$claude_dir/settings.json"
        fi
      fi

      # Interactive CLAUDE.md merge
      if [[ -f "$config_dir/CLAUDE.md" ]]; then
        if $DRY_RUN; then
          printf '  dry-run merge-claude-md.py -> %s/CLAUDE.md\n' "$claude_dir"
        else
          PROJECT_CONVENTIONS_AGENT="${PROJECT_CONVENTIONS_AGENT:-}" \
            "$(get_python)" "$REPO_ROOT/scripts/merge-claude-md.py" \
              --template "$config_dir/CLAUDE.md" \
              --target "$claude_dir/CLAUDE.md"
        fi
      fi

      # Jenkins MCP: create venv and register if not already done
      local jenkins_dir="$claude_dir/tools/jenkins-monitor"
      if [[ -d "$jenkins_dir" ]]; then
        if $DRY_RUN; then
          printf '  dry-run jenkins MCP setup\n'
        else
          if [[ ! -d "$jenkins_dir/.venv" ]]; then
            header "Setting up Jenkins MCP venv"
            (cd "$jenkins_dir" && \
              { python3 -m venv .venv || python -m venv .venv; } && \
              .venv/bin/pip install -r requirements.txt -q)
            ok "Jenkins venv created"
          fi
          if ! claude mcp get jenkins-monitor &>/dev/null; then
            claude mcp add jenkins-monitor -s user -- \
              "$jenkins_dir/.venv/bin/python3" \
              "$jenkins_dir/server.py"
            ok "Jenkins MCP registered"
          else
            ok "Jenkins MCP already registered"
          fi
        fi
      fi

      # zshrc reminder
      if ! $DRY_RUN; then
        printf '\n%s\n' "$(printf '%0.s─' {1..60})"
        printf 'Manual: add to ~/.zshrc if not already present:\n\n'
        printf '   # Jenkins MCP credentials\n'
        printf '   export JENKINS_URL="https://your-jenkins.com"\n'
        printf '   export JENKINS_USER="your-username"\n'
        printf '   export JENKINS_TOKEN="your-token"\n\n'
        printf '   # Claude Code / Codex CLI session cleanup\n'
        printf "   trap '[[ -n \"\$TERM_SESSION_ID\" ]] && rm -rf \"\$HOME/.claude/review/\$TERM_SESSION_ID\" \"\$HOME/.codex/review/\$TERM_SESSION_ID\" 2>/dev/null' EXIT\n"
        printf '%s\n\n' "$(printf '%0.s─' {1..60})"
      else
        printf '  dry-run zshrc-reminder (would print manual setup instructions)\n'
      fi
      ;;
  esac
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --to) TOOL="${2:-}"; shift 2 ;;
    --source) SOURCE_DIR="${2:-}"; shift 2 ;;
    --tools-source) TOOLS_SOURCE_DIR="${2:-}"; shift 2 ;;
    --claude-dest) CLAUDE_DEST="${2:-}"; shift 2 ;;
    --codex-dest) CODEX_DEST="${2:-}"; shift 2 ;;
    --claude-tools) CLAUDE_TOOLS_DEST="${2:-}"; shift 2 ;;
    --codex-tools) CODEX_TOOLS_DEST="${2:-}"; shift 2 ;;
    --include) INCLUDE="${2:-}"; shift 2 ;;
    --replace) REPLACE=true; shift ;;
    --no-preflight) PREFLIGHT=false; shift ;;
    --dry-run) DRY_RUN=true; shift ;;
    --help|-h) usage ;;
    *) err "Unknown option: $1"; usage ;;
  esac
done

case "$TOOL" in
  claude|codex|all) ;;
  *) err "Unsupported --to '$TOOL'. Use claude, codex, or all."; exit 1 ;;
esac

sync_commands
