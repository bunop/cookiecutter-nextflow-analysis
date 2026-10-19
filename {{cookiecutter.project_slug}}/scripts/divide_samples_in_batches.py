#! /usr/bin/env python3

# A simple script to divide samples in batches for parallel processing relying on
# the size of each sample, as reported by `seqkit stats`. Stats are joined to the
# samplesheet by file path, so no assumption is made on sample names.

import os
import csv
import sys
import argparse
import collections


def parse_args():
    parser = argparse.ArgumentParser(
        description="Divide samples in batches for parallel processing")
    parser.add_argument(
        "--samplesheet",
        required=True,
        help="Input samplesheet file"
    )
    parser.add_argument(
        "--num_batches",
        type=int,
        default=6,
        help="Number of batches to divide samples into (default: %(default)s)"
    )
    parser.add_argument(
        "--stats",
        required=True,
        help="Input statistics file (seqkit stats output, with or without -T)"
    )
    parser.add_argument(
        "--column",
        default="sum_len",
        help="Stats column used as sample size (default: %(default)s)"
    )
    parser.add_argument(
        "-o",
        "--output_prefix",
        required=True,
        help="Prefix for output batch files"
    )
    return parser.parse_args()


def idx_to_label(n):
    s = ''
    while True:
        s = chr(ord('a') + (n % 26)) + s
        n //= 26
        if n == 0:
            break
    if len(s) < 2:
        s = 'a' + s
    return s


def read_stats(path, column):
    """Return two dicts: {realpath: size} and {basename: [sizes]}"""

    by_path = {}
    by_name = collections.defaultdict(list)
    header = None

    with open(path) as stats_fh:
        for line in stats_fh:
            # shortcut: whitespace split breaks on paths with spaces, use a real tsv reader if needed
            parts = line.split()

            if not parts:
                continue

            if header is None:
                header = parts
                if column not in header:
                    sys.exit(f"ERROR: column '{column}' not found in {path}: {header}")
                col_idx = header.index(column)
                continue

            # xargs may call seqkit more than once: skip repeated headers
            if parts == header:
                continue

            file_ = parts[0]
            size = int(float(parts[col_idx].replace(",", "")))

            by_path[os.path.realpath(file_)] = size
            by_name[os.path.basename(file_)].append(size)

    return by_path, by_name


def get_size(file_, by_path, by_name):
    """Find a file size by real path, falling back to an unique basename"""

    real = os.path.realpath(file_)
    if real in by_path:
        return by_path[real]

    sizes = by_name.get(os.path.basename(file_), [])
    if len(sizes) == 1:
        return sizes[0]

    if len(sizes) > 1:
        sys.exit(f"ERROR: '{file_}' basename is ambiguous in stats file, run seqkit with absolute paths")

    sys.exit(f"ERROR: no stats found for '{file_}'")


if __name__ == "__main__":
    args = parse_args()

    by_path, by_name = read_stats(args.stats, args.column)

    with open(args.samplesheet) as samplesheet_fh:
        samplesheet_lines = list(csv.reader(samplesheet_fh, delimiter=","))

    header = samplesheet_lines[0]
    samplesheet_lines = [line for line in samplesheet_lines[1:] if line]

    # sample is the 'sample' column, if any, else the first one
    sample_idx = header.index("sample") if "sample" in header else 0
    file_idxs = [
        i for i, col in enumerate(header) if col.startswith("fastq") or col == "path"]

    if not file_idxs:
        sys.exit(f"ERROR: no fastq/path columns found in samplesheet header: {header}")

    # a sample size is the sum of all its files (all lanes, R1 + R2)
    sample_sizes = collections.Counter()

    for line in samplesheet_lines:
        sample = line[sample_idx]
        for i in file_idxs:
            if i < len(line) and line[i]:
                sample_sizes[sample] += get_size(line[i], by_path, by_name)

    # sort samples by size (descending)
    stats = sample_sizes.most_common()

    # now we need to divide samples in batches: simple iterate over stats records
    # put every record in a different batch, then start again from the first batch
    batches = [[] for _ in range(args.num_batches)]

    for i, record in enumerate(stats):
        batches[i % args.num_batches].append(record)

    # Counter per tracciare quante volte ogni sample viene scritto
    written_counter = collections.Counter()

    # iterate over batches and write a new samplesheet for each batch
    for i, batch in enumerate(batches):
        # keep batch order (by size, descending) in the output samplesheet
        order = {sample: j for j, (sample, _) in enumerate(batch)}
        lines = sorted(
            (line for line in samplesheet_lines if line[sample_idx] in order),
            key=lambda line: order[line[sample_idx]])

        suffix = idx_to_label(i)
        output_file = f"{args.output_prefix}_{suffix}.csv"

        with open(output_file, "w") as out_fh:
            writer = csv.writer(out_fh, delimiter=",", lineterminator="\n")
            writer.writerow(header)

            for line in lines:
                writer.writerow(line)

        written_counter.update(order.keys())

        # print batch summary
        print(f"Batch {suffix}: {len(batch)} samples, {args.column}={sum(x[1] for x in batch)} -> {output_file}")

    # Check if all samples were written exactly once
    all_samples = set(line[sample_idx] for line in samplesheet_lines)
    not_written = all_samples - set(written_counter.keys())
    written_more_than_once = [s for s, c in written_counter.items() if c > 1]

    if not_written:
        print(f"WARNING: those samples were not written in any file: {not_written}")
    if written_more_than_once:
        print(f"WARNING: the following samples were written more than once: {written_more_than_once}")
    if not not_written and not written_more_than_once:
        print("All samples were written exactly once in the batches.")
