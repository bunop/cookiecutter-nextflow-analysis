---
name: clean-csv
description: Clean a CSV file (metadata, samplesheet) with scripts/clean_csv.py - remove the UTF-8 BOM and the rows and columns that are completely empty, including rows made only of delimiters (",,,,"). Use when the user asks to remove the BOM or empty rows/columns, or when csvkit/make_samplesheet.py fail with "column not found" on the first header name or read blank rows.
---

# Clean a CSV

Goal: a clean copy of a CSV (no BOM, no empty rows or columns) before it is
used as metadata or samplesheet. Rules on where and how to run commands: see
`CLAUDE.md`.

## 1. Look at the file

```bash
head -c 3 <file> | xxd          # ef bb bf = UTF-8 BOM
head -n 3 <file>; tail -n 3 <file>
```

Excel exports often end with rows like `,,,,` and have unnamed empty columns.
Raw files in `data/` and `conf/samplesheet.csv` are never modified without an
explicit confirmation: write a new file (e.g. `conf/metadata_clean.csv`).

## 2. Run the script

```bash
python3 scripts/clean_csv.py <file> -o <clean file>
```

- A row is empty when all its cells are blank (a blank line or only
  delimiters); a column is dropped when its header and all its values are blank.
- A column with a header but no values is **kept** and reported as a warning:
  ask the user, then add `--drop-empty-headed-columns` if it can go.
- The delimiter (`,` `;` TAB) is detected from the first line, override it with
  `--delimiter`. Quoted cells (even with newlines) are preserved.
- The summary on stderr reports the BOM, the delimiter and what was dropped:
  show it to the user and check the row count (`wc -l`, `csvstat --count`).
- `--in-place` overwrites the input: only after the user asked for it.
- A non UTF-8 file (e.g. latin-1) stops with an error: convert it first
  (`iconv -f latin1 -t utf-8`), do not guess.

## 3. Document

Add a line to the README (file, command, what was dropped) and commit the
cleaned file and the README together, if the file is tracked.
