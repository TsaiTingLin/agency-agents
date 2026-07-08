#!/usr/bin/env python3
"""mentor_retrospective — Stop hook.

Fires when the Claude Code session ends.
Reminds user to run mentor-check-commit for retrospective if a session is active.
Cleanup is handled by the .zshrc EXIT trap — this hook no longer calls cleanup_session().
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from mentor_memory import get_session_dir


def main() -> int:
    session_dir = get_session_dir()

    if session_dir:
        print("\n" + "═" * 60)
        print("  Quality Gate Session 結束")
        print("═" * 60)
        print("  如果任務已完成，執行 /quality-gate mentor-check-commit")
        print("  做 retrospective 後再關閉 terminal。")
        print("═" * 60 + "\n")

    return 0


if __name__ == "__main__":
    sys.exit(main())
