#!/usr/bin/env python3
"""Fix Markdown table rows broken by Notion's export.

When a Notion table cell contains a newline, Notion's "Export as Markdown &
CSV" turns that newline into a literal line break in the .md file. The result
is one logical table row split across several physical lines, which breaks
the Markdown table structure (every continuation line after the first is
missing its column separators).

This script detects that pattern and repairs it: continuation lines belonging
to the same row are rejoined onto one line, with the original newline
represented as an HTML `<br>` inside the cell (the standard way to keep a
line break inside a Markdown table cell). Rows that were never broken are
left byte-for-byte identical.

Usage:
    python fix_notion_tables.py [target ...] [--check]

    target   A .md file, a directory (scanned recursively for *.md), or
              omitted entirely to scan the current directory. Multiple
              targets may be given.
    --check  Report what would change without writing anything (exit code 1
              if any file would change, 0 otherwise). Useful in CI or before
              committing a fresh Notion export.

Exit code is always 0 in normal (non --check) mode; individual file read/
write errors are reported but do not stop the run.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Directories that are never worth walking into when scanning a project root.
_SKIP_DIR_NAMES = {".git", "node_modules", ".claude", ".venv", "venv", "__pycache__"}


def fix_table_newlines(content: str) -> str:
    """Rejoin table rows that Notion's export split across multiple lines.

    A table row always starts with '|'. A properly closed row's last
    non-whitespace character is also '|'. When a row's cell contains a
    newline, the line Notion emits for that row does NOT end with '|' -
    the rest of the row (the remaining cells) shows up on the following
    physical line(s) instead. So: whenever a '|'-started line doesn't yet
    end with '|', treat every following line as a continuation of the same
    cell (joined with '<br>') until one finally does end with '|'.

    This also correctly handles a blank line landing in the middle of a
    broken cell (Notion emits those too, e.g. a paragraph break inside the
    cell) - the blank line is just another continuation line to absorb.
    """
    lines = content.split("\n")
    result: list[str] = []
    i = 0
    n = len(lines)

    while i < n:
        line = lines[i]

        if line.startswith("|"):
            accumulated = line
            # Keep absorbing lines until the row is actually closed by a
            # trailing '|'. Stop at end-of-file even if never closed, so a
            # malformed/truncated table can't loop forever.
            while not accumulated.rstrip().endswith("|") and i + 1 < n:
                i += 1
                accumulated = accumulated + "<br>" + lines[i]
            result.append(accumulated)
        else:
            result.append(line)

        i += 1

    return "\n".join(result)


def iter_markdown_files(targets: list[Path]) -> list[Path]:
    files: list[Path] = []
    seen: set[Path] = set()

    def add(p: Path) -> None:
        resolved = p.resolve()
        if resolved not in seen:
            seen.add(resolved)
            files.append(p)

    for target in targets:
        if target.is_file():
            add(target)
        elif target.is_dir():
            for path in sorted(target.rglob("*.md")):
                if any(part in _SKIP_DIR_NAMES for part in path.parts):
                    continue
                add(path)
        else:
            print(f"skip (not found): {target}", file=sys.stderr)

    return files


def process_file(path: Path, check_only: bool) -> str:
    """Returns one of: 'fixed', 'unchanged', 'error'."""
    try:
        original = path.read_text(encoding="utf-8")
    except (UnicodeDecodeError, OSError) as exc:
        print(f"ERROR reading {path}: {exc}", file=sys.stderr)
        return "error"

    fixed = fix_table_newlines(original)

    if fixed == original:
        return "unchanged"

    if not check_only:
        try:
            path.write_text(fixed, encoding="utf-8")
        except OSError as exc:
            print(f"ERROR writing {path}: {exc}", file=sys.stderr)
            return "error"

    return "fixed"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("targets", nargs="*", default=["."], help="File(s) or directory(ies) to fix (default: current directory)")
    parser.add_argument("--check", action="store_true", help="Report only; do not modify files")
    args = parser.parse_args()

    target_paths = [Path(t) for t in args.targets]
    files = iter_markdown_files(target_paths)

    if not files:
        print("No .md files found under the given target(s).")
        return 0

    counts = {"fixed": 0, "unchanged": 0, "error": 0}
    for path in files:
        status = process_file(path, check_only=args.check)
        counts[status] += 1
        if status == "fixed":
            verb = "Would fix" if args.check else "Fixed"
            print(f"{verb}: {path}")

    print(
        f"\n{counts['fixed']} fixed, {counts['unchanged']} unchanged, "
        f"{counts['error']} error(s) out of {len(files)} file(s) checked."
    )

    if args.check and counts["fixed"] > 0:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
