#!/usr/bin/env python3
"""Mentor memory management — stores working memory for mentor checks.

Each terminal session gets an isolated directory under <tool-dir>/review/<session-id>/.
The review base is derived from the script's own location — ~/.claude/tools → ~/.claude/review,
~/.codex/tools → ~/.codex/review — so each AI tool has fully isolated session storage.
Session ID priority: TERM_SESSION_ID (macOS Terminal) → ITERM_SESSION_ID (iTerm2) → CLAUDE_CODE_SESSION_ID (fallback).
TERM_SESSION_ID is used as primary because it's available in both hook env and terminal shell (EXIT trap).

On terminal close, the .zshrc EXIT trap deletes the directory directly.
On init, directories older than 24 hours are also cleaned up (handles crashes).

CLI usage:
  python3 mentor_memory.py init                             — initialise session dir, clean old dirs
  python3 mentor_memory.py get                              — print session dir path (exits 1 if none)
  python3 mentor_memory.py write-requirements               — read stdin, write to requirements.md
  python3 mentor_memory.py read-requirements                — print requirements.md contents
  python3 mentor_memory.py read-log                         — print mentor-log.md contents
  python3 mentor_memory.py log-issue '<問題>' '<原因>' '<解法>'  — append table row to issues.md
  python3 mentor_memory.py read-issues                      — print issues.md contents
  python3 mentor_memory.py cleanup                          — delete session dir
"""

import os
import sys
import shutil
from datetime import datetime, timedelta
from pathlib import Path


def _term_session_id() -> str | None:
    return (os.environ.get("TERM_SESSION_ID")
            or os.environ.get("ITERM_SESSION_ID")
            or os.environ.get("CLAUDE_CODE_SESSION_ID"))


def _review_base() -> Path:
    # ~/.claude/tools/mentor_memory.py → ~/.claude/review/
    # ~/.codex/tools/mentor_memory.py  → ~/.codex/review/
    return Path(__file__).parent.parent / "review"


def get_session_dir() -> Path | None:
    sid = _term_session_id()
    if not sid:
        return None
    d = _review_base() / sid
    return d if d.exists() else None


def init_session() -> Path:
    sid = _term_session_id()
    if not sid:
        raise RuntimeError("$TERM_SESSION_ID is not set — cannot initialise session")
    session_dir = _review_base() / sid
    session_dir.mkdir(parents=True, exist_ok=True)
    _cleanup_old_sessions()
    return session_dir


def _cleanup_old_sessions() -> None:
    """Delete session dirs older than 24 hours (handles crashes / missed EXIT traps)."""
    base = _review_base()
    if not base.exists():
        return
    cutoff = datetime.now() - timedelta(hours=24)
    current_sid = _term_session_id()
    for d in base.iterdir():
        if not d.is_dir():
            continue
        if d.name == current_sid:
            continue
        try:
            mtime = datetime.fromtimestamp(d.stat().st_mtime)
            if mtime < cutoff:
                shutil.rmtree(d, ignore_errors=True)
        except OSError:
            pass


def cleanup_session() -> None:
    sid = _term_session_id()
    if not sid:
        return
    d = _review_base() / sid
    if d.exists():
        shutil.rmtree(d, ignore_errors=True)


def write_requirements(content: str) -> None:
    session_dir = get_session_dir() or init_session()
    (session_dir / "requirements.md").write_text(content)


def read_requirements() -> str:
    session_dir = get_session_dir()
    if not session_dir:
        return ""
    f = session_dir / "requirements.md"
    return f.read_text() if f.exists() else ""


def read_log() -> str:
    session_dir = get_session_dir()
    if not session_dir:
        return ""
    f = session_dir / "mentor-log.md"
    return f.read_text() if f.exists() else ""


def log_issue(problem: str, cause: str, solution: str) -> None:
    session_dir = get_session_dir() or init_session()
    f = session_dir / "issues.md"
    if not f.exists():
        with open(f, "w") as fp:
            fp.write("| 問題 | 發生原因 | 解法 |\n")
            fp.write("|------|---------|------|\n")
    with open(f, "a") as fp:
        fp.write(f"| {problem} | {cause} | {solution} |\n")


def read_issues() -> str:
    session_dir = get_session_dir()
    if not session_dir:
        return ""
    f = session_dir / "issues.md"
    return f.read_text() if f.exists() else ""


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""

    if cmd == "init":
        d = init_session()
        print(str(d))

    elif cmd == "get":
        d = get_session_dir()
        if d:
            print(str(d))
        else:
            sys.exit(1)

    elif cmd == "write-requirements":
        content = sys.stdin.read()
        write_requirements(content)
        print("requirements.md written")

    elif cmd == "read-requirements":
        print(read_requirements())

    elif cmd == "read-log":
        print(read_log())

    elif cmd == "log-issue":
        if len(sys.argv) >= 5:
            log_issue(sys.argv[2], sys.argv[3], sys.argv[4])
            print("issue logged")
        else:
            print("Usage: log-issue '<問題>' '<原因>' '<解法>'", file=sys.stderr)
            sys.exit(1)

    elif cmd == "read-issues":
        print(read_issues())

    elif cmd == "cleanup":
        cleanup_session()
        print("session cleaned up")

    else:
        print(__doc__)
        sys.exit(1)
