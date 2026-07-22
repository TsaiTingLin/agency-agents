#!/usr/bin/env python3
"""Merge agency-agents settings template into ~/.claude/settings.json.

Only adds missing entries — never overwrites existing values.
"""

import argparse
import json
import shutil
import sys
from pathlib import Path


def find_python_bin():
    """Return absolute path of python3 or python, exit if neither found."""
    python = shutil.which("python3") or shutil.which("python")
    if not python:
        print("[ERR] No python3 or python found — cannot continue", file=sys.stderr)
        sys.exit(1)
    return python


def substitute(text, home, python_bin):
    """Replace {{HOME}} and python3 command with resolved values."""
    text = text.replace("{{HOME}}", home)
    # Replace python3 in hook commands with the detected binary path
    text = text.replace('"python3 ', f'"{python_bin} ')
    return text


def _cmd_signature(command):
    """Command identity ignoring which python interpreter path runs it, so
    re-running merge with a different resolved python3 path (e.g. plain
    'python3' vs '/opt/homebrew/bin/python3') is recognized as the same hook
    instead of being appended as a duplicate."""
    parts = command.split(None, 1)
    return parts[1] if len(parts) > 1 else command


def merge_hooks(target_hooks, template_hooks):
    """Add hook commands from template that are not already in target."""
    for event, template_entries in template_hooks.items():
        if event not in target_hooks:
            target_hooks[event] = template_entries
            continue
        existing_sigs = set()
        for entry in target_hooks[event]:
            for hook in entry.get("hooks", []):
                existing_sigs.add(_cmd_signature(hook.get("command", "")))
        for entry in template_entries:
            for hook in entry.get("hooks", []):
                if _cmd_signature(hook.get("command", "")) not in existing_sigs:
                    target_hooks[event].append(entry)
    return target_hooks


def merge_deny(target_deny, template_deny):
    """Add deny rules from template that are not already in target."""
    existing = set(target_deny)
    for rule in template_deny:
        if rule not in existing:
            target_deny.append(rule)
    return target_deny


def main(template_path, target_path):
    home = str(Path.home())
    python_bin = find_python_bin()

    template_text = Path(template_path).read_text()
    template_text = substitute(template_text, home, python_bin)
    template = json.loads(template_text)

    target_file = Path(target_path)
    target = json.loads(target_file.read_text()) if target_file.exists() else {}

    if "hooks" in template:
        target.setdefault("hooks", {})
        target["hooks"] = merge_hooks(target["hooks"], template["hooks"])

    if "permissions" in template and "deny" in template["permissions"]:
        target.setdefault("permissions", {})
        target["permissions"].setdefault("deny", [])
        target["permissions"]["deny"] = merge_deny(
            target["permissions"]["deny"],
            template["permissions"]["deny"],
        )

    target_file.write_text(json.dumps(target, indent=4, ensure_ascii=False) + "\n")
    print(f"[OK]  settings.json merged -> {target_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--template", required=True, help="Path to settings template")
    parser.add_argument("--target", required=True, help="Path to ~/.claude/settings.json")
    args = parser.parse_args()
    main(args.template, args.target)
