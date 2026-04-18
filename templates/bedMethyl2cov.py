#!/usr/bin/env python

import csv
import gzip
import pathlib
import logging
import argparse

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

IDX_CHROM = 0
IDX_CHROM_START = 1
IDX_CHROM_END = 2
IDX_NAME = 3
IDX_SCORE = 4
IDX_STRAND = 5
IDX_PERCENT_MODIFIED = 10
IDX_COUNT_MODIFIED = 11
IDX_COUNT_CANONICAL = 12


def parse_bedmethyl_line(line: str, line_number: int, filename: pathlib.Path):
    fields = line.rstrip("\n").split("\t")

    if len(fields) < 18:
        raise ValueError(
            f"Record {line_number} in {filename} has {len(fields)} fields, expected >= 18"
        )

    strand = fields[IDX_STRAND]
    if strand not in ["+", "-", "."]:
        raise ValueError(
            f"Record {line_number} in {filename} is invalid: Invalid strand '{strand}'"
        )

    chrom = fields[IDX_CHROM]
    chrom_start = int(fields[IDX_CHROM_START])
    chrom_end = int(fields[IDX_CHROM_END])
    name = fields[IDX_NAME]
    score = int(fields[IDX_SCORE])
    input_percent_modified = float(fields[IDX_PERCENT_MODIFIED])
    count_modified = int(fields[IDX_COUNT_MODIFIED])
    count_canonical = int(fields[IDX_COUNT_CANONICAL])

    custom_score = count_modified + count_canonical
    denominator = custom_score

    if denominator == 0:
        percent_modified = 0.0
    else:
        percent_modified = round((count_modified / denominator) * 100, 2)

    if percent_modified != input_percent_modified:
        logger.debug(
            f"Percent modified mismatch: modkit:{input_percent_modified} vs self:"
            f"{percent_modified} for {name} at {chrom}:{chrom_start}-{chrom_end}"
        )

    return (
        name,
        score,
        custom_score,
        chrom,
        chrom_start + 1,
        chrom_end,
        percent_modified,
        count_modified,
        count_canonical,
    )


def open_bedMethyl_file(filename: pathlib.Path, mode='rt'):
    """
    Open a BED file (possibly gzipped) for reading.
    """

    opener = gzip.open if filename.suffix == '.gz' else open
    processed = 0

    with opener(filename, mode) as handle:
        for i, line in enumerate(handle, start=1):
            if i % 100000 == 0:
                logger.info(f"Processing record {i} in {filename}")

            yield parse_bedmethyl_line(line, i, filename)
            processed = i

    logger.info(f"Processed {processed} records in {filename}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Convert a bedMethyl file to a coverage file."
    )
    parser.add_argument(
        "-i", "--input_folder", required=True,
        help="Input folder containing bedMethyl files",
        type=pathlib.Path
    )
    parser.add_argument(
        "-o", "--output", required=True,
        help="Output folder for the coverage data",
        type=pathlib.Path
    )
    parser.add_argument(
        "-s", "--score", type=int,
        help="Minimum score for filtering records (default: %(default)s)",
    )
    parser.add_argument(
        "--custom_score", type=int, default=1,
        help=(
            "Custom score for filtering records (intended as count_modified + "
            "count_canonical - default: %(default)s)"
        )
    )
    parser.add_argument(
        "--force", action='store_true', default=False,
        help="Force overwrite of output files if they already exist (default: %(default)s)"
    )
    args = parser.parse_args()

    if not args.input_folder.is_dir():
        logger.error(
            f"Input folder '{args.input_folder}' does not exist or is not a directory.")
        exit(1)

    args.output.mkdir(parents=True, exist_ok=args.force)

    logger.info(f"Processing input folder: {args.input_folder}")

    for bed_file in args.input_folder.rglob("*.bed.gz"):
        logger.debug(f"Processing file: {bed_file.relative_to(args.input_folder)}")

        output_prefix = args.output / (bed_file.name.split('.bed')[0])

        handles = {}
        writers = {}

        for record in open_bedMethyl_file(bed_file):
            (
                name,
                score,
                custom_score,
                chrom,
                chrom_start_1_based,
                chrom_end,
                percent_modified,
                count_modified,
                count_canonical,
            ) = record

            if args.score and score < args.score:
                continue

            if args.custom_score and custom_score < args.custom_score:
                continue

            if name not in handles:
                output_file = output_prefix.with_suffix(f".{name}.cov.gz")
                logger.info(f"Creating output file: {output_file}")
                out_handle = gzip.open(output_file, mode='wt')
                handles[name] = out_handle
                writers[name] = out_handle.write

            write_line = writers[name]
            write_line(
                f"{chrom}\t{chrom_start_1_based}\t{chrom_end}\t{percent_modified}\t"
                f"{count_modified}\t{count_canonical}\n"
            )

        for handle in handles.values():
            handle.close()

    logger.info(f"Output written to: {args.output}")
    logger.info("Processing complete.")
