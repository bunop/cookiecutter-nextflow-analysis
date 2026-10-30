#! /usr/bin/env python3

# clean a CSV file: remove the UTF-8 BOM and the rows and columns that are
# completely empty (a row made only of delimiters is empty)

import io
import os
import sys
import csv
import codecs
import argparse

DELIMITERS = ",;\t"


def parse_args():
    parser = argparse.ArgumentParser(
        description="Remove the UTF-8 BOM and the completely empty rows and columns from a CSV file")
    parser.add_argument("input", help="CSV file to clean")
    output = parser.add_mutually_exclusive_group()
    output.add_argument(
        "-o", "--output",
        help="Output file (default: stdout)")
    output.add_argument(
        "--in-place", action="store_true",
        help="Overwrite the input file")
    parser.add_argument(
        "--delimiter",
        help="Field delimiter (default: the most frequent of , ; TAB in the first non empty line)")
    parser.add_argument(
        "--drop-empty-headed-columns", action="store_true",
        help="Drop also the columns with a header but no values (default: they are kept)")
    return parser.parse_args()


def detect_delimiter(text):
    first = next((line for line in text.splitlines() if line.strip(DELIMITERS + " \r\n")), "")
    counts = {delimiter: first.count(delimiter) for delimiter in DELIMITERS}
    best = max(counts, key=counts.get)
    return best if counts[best] else ","


def is_empty(cell):
    return not cell.strip()


if __name__ == "__main__":
    args = parse_args()

    with open(args.input, "rb") as handle:
        raw = handle.read()

    has_bom = raw.startswith(codecs.BOM_UTF8)

    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError as e:
        sys.exit(f"ERROR: {args.input} is not UTF-8: {e}")

    delimiter = args.delimiter or detect_delimiter(text)

    rows = list(csv.reader(io.StringIO(text, newline=""), delimiter=delimiter))
    kept = [row for row in rows if not all(is_empty(cell) for cell in row)]
    dropped_rows = len(rows) - len(kept)

    if not kept:
        sys.exit(f"ERROR: {args.input} has no data")

    # pad the short rows so that columns can be compared
    width = max(len(row) for row in kept)
    kept = [row + [""] * (width - len(row)) for row in kept]

    header, data = kept[0], kept[1:]
    keep_idx, dropped_cols, kept_empty = [], [], []

    for i in range(width):
        no_values = all(is_empty(row[i]) for row in data)

        if no_values and is_empty(header[i]):
            dropped_cols.append(f"#{i + 1}")
        elif no_values and args.drop_empty_headed_columns:
            dropped_cols.append(header[i])
        else:
            keep_idx.append(i)
            if no_values:
                kept_empty.append(header[i])

    out = io.StringIO()
    writer = csv.writer(out, delimiter=delimiter, lineterminator="\n")
    for row in kept:
        writer.writerow([row[i] for i in keep_idx])

    payload = out.getvalue().encode("utf-8")

    if args.in_place or args.output:
        target = args.input if args.in_place else args.output
        tmp = f"{target}.tmp"
        with open(tmp, "wb") as handle:
            handle.write(payload)
        os.replace(tmp, target)
    else:
        sys.stdout.buffer.write(payload)

    print(
        f"BOM: {'removed' if has_bom else 'not found'}; delimiter: {delimiter!r}; "
        f"empty rows dropped: {dropped_rows}; empty columns dropped: {len(dropped_cols)} "
        f"{dropped_cols if dropped_cols else ''}".rstrip(),
        file=sys.stderr)

    if kept_empty:
        print(f"WARNING: columns with a header but no values kept: {kept_empty} "
              "(use --drop-empty-headed-columns to drop them)", file=sys.stderr)
