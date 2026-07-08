#!/usr/bin/env python3
"""Interactively merge missing sections from CLAUDE.md template into target.

Sections are identified by ## headings. Never overwrites existing content.
"""

import argparse
import os
from pathlib import Path


def get_sections(text):
    """Return list of (heading_line, full_section_text) for each ## section."""
    sections = []
    current_heading = None
    current_lines = []

    for line in text.splitlines(keepends=True):
        if line.startswith("## "):
            if current_heading is not None:
                sections.append((current_heading.strip(), "".join(current_lines)))
            current_heading = line
            current_lines = [line]
        elif current_heading is not None:
            current_lines.append(line)

    if current_heading is not None:
        sections.append((current_heading.strip(), "".join(current_lines)))

    return sections


def substitute(text, home, project_repo, conventions_agent):
    text = text.replace("{{HOME}}", home)
    if project_repo:
        text = text.replace("{{PROJECT_REPO}}", project_repo)
    if conventions_agent:
        text = text.replace("{{PROJECT_CONVENTIONS_AGENT}}", conventions_agent)
    return text


def main(template_path, target_path):
    home = str(Path.home())
    project_repo = os.environ.get("PROJECT_REPO", "")
    h2_agent = os.environ.get("PROJECT_CONVENTIONS_AGENT", "")

    template_text = Path(template_path).read_text()
    template_text = substitute(template_text, home, project_repo, h2_agent)
    template_sections = get_sections(template_text)

    target_file = Path(target_path)

    if not target_file.exists():
        ans = input(f"\n{target_path} does not exist. Create it with full template? (y/n): ").strip().lower()
        if ans == "y":
            target_file.parent.mkdir(parents=True, exist_ok=True)
            target_file.write_text(template_text)
            print(f"[OK]  Created {target_path}")
        else:
            print("Skipped.")
        return

    target_text = target_file.read_text()
    target_headings = {h for h, _ in get_sections(target_text)}

    missing = [(h, c) for h, c in template_sections if h not in target_headings]

    if not missing:
        print("[OK]  CLAUDE.md is up to date — nothing to add")
        return

    print(f"\nFound sections not in your CLAUDE.md:")
    for i, (heading, _) in enumerate(missing, 1):
        label = heading.lstrip("#").strip()
        print(f"  [{i}] {label}")

    ans = input("\nAdd which sections? (e.g. 1 2 3 / all / none): ").strip().lower()

    if ans in ("none", ""):
        print("Skipped.")
        return

    if ans == "all":
        selected = missing
    else:
        indices = []
        for token in ans.split():
            if token.isdigit():
                idx = int(token) - 1
                if 0 <= idx < len(missing):
                    indices.append(idx)
        selected = [missing[i] for i in indices]

    if not selected:
        print("Nothing selected.")
        return

    with target_file.open("a") as f:
        f.write("\n")
        for _, content in selected:
            f.write(content)
            if not content.endswith("\n"):
                f.write("\n")

    print(f"[OK]  Added {len(selected)} section(s) to {target_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--template", required=True)
    parser.add_argument("--target", required=True)
    args = parser.parse_args()
    main(args.template, args.target)
