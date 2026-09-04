---
name: fix-notion-tables
description: Fix Markdown tables broken by Notion's "Export as Markdown & CSV" feature. Whenever a table cell in Notion contains a newline, the export turns it into a literal line break in the .md file, splitting one table row across several physical lines and corrupting the table. Use this skill any time markdown files in this project (especially old_docs/, 機能仕様/, 画面定義/, 共通系仕様/) were just re-exported from Notion, or when the user asks to check for or fix "崩れ" / broken / garbled table formatting, tables with line breaks in the wrong place, or tables that don't render correctly after a Notion export. This bug reliably reappears on every fresh export, so proactively suggest running this after any Notion export work even if the user only asked to "update the docs."
---

# Fix Notion table exports

## Why this happens

Notion's Markdown export represents a table row as a single line starting
and ending with `|`. But if a cell's content contains a newline (a
paragraph break the author typed inside the cell), the export writes that
newline literally into the file instead of encoding it. The row is then
split across multiple physical lines, and every line after the first is
missing its column separators — the table renders broken wherever that
happened.

This is a mechanical, deterministic corruption with a mechanical,
deterministic fix: don't re-derive the algorithm by hand or with ad hoc
`grep`/`sed`. Use `scripts/fix_notion_tables.py`, which already implements
it correctly (including edge cases like a blank line landing mid-cell, or a
cell that legitimately contains a `|` character).

## How to use it

Run the script against whatever was just exported — a single file, a
directory, or (rarely) the whole project:

```bash
python3 .claude/skills/fix-notion-tables/scripts/fix_notion_tables.py old_docs/
```

- Pass one or more paths as arguments (files and/or directories). A
  directory is scanned recursively for `*.md` files.
- With no arguments it scans the current directory.
- Add `--check` to see what *would* change without writing anything — use
  this before committing if you want to review the diff yourself first, or
  in a pre-commit/CI check (exit code 1 means something needs fixing).

The script prints one line per file it changes and a summary count at the
end. Files that are already correctly formatted are left completely
untouched (byte-for-byte), so it is always safe to run — including
repeatedly on files you already fixed.

## Typical workflow in this project

1. Export or re-export pages from Notion into `old_docs/` (or wherever the
   target files live).
2. Run the script against the affected paths, e.g.:
   ```bash
   python3 .claude/skills/fix-notion-tables/scripts/fix_notion_tables.py old_docs/ 機能仕様/ 画面定義/ 共通系仕様/
   ```
3. Review the reported list of fixed files. `git diff` them to confirm the
   only changes are table-row joins (each fix replaces the row's internal
   newlines with `<br>` and merges it back onto one line) — if you see
   unrelated content changes mixed in, that's real content that changed in
   Notion, not something this script introduced.
4. Commit as usual.

If asked to "check whether the exported files are broken" without also
being asked to fix them, run with `--check` first and report the result
before writing anything.
