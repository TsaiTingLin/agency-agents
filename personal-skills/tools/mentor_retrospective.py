#!/usr/bin/env python3
"""mentor_retrospective — Stop hook.

Fires whenever the Claude Code agent loop stops (i.e. on most turns, not just
session end). Reminds user to run mentor-check-commit only when there are
actually recorded issues to retrospect on, so the reminder doesn't repeat on
every turn of a session that never called /reflect.
Cleanup is handled by the .zshrc EXIT trap — this hook no longer calls cleanup_session().
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from mentor_memory import read_issues


def main() -> int:
    if read_issues().strip():
        print("\n" + "═" * 60)
        print("  Quality Gate Session 結束")
        print("═" * 60)
        print("  如果任務已完成，執行 /quality-gate mentor-check-commit")
        print("  做 retrospective 後再關閉 terminal。")
        print("═" * 60 + "\n")

    return 0


if __name__ == "__main__":
    sys.exit(main())
