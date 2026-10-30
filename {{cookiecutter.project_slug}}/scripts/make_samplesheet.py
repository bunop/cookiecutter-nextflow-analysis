#! /usr/bin/env python3

# create a samplesheet csv file from path names

import re
import sys
import csv
import logging
import pathlib
import argparse
from typing import Tuple, List, Dict, Generator

# Check Python version
if sys.version_info < (3, 6):
    sys.stderr.write("Error: Python 3.6 or higher is required.\n")
    sys.exit(1)

logger = logging.getLogger(__name__)

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Create a samplesheet CSV file from path names.")
    parser.add_argument(
        "--path",
        type=pathlib.Path,
        nargs="+",
        required=True,
        help="Path(s) to the directory/directories containing sample folders."
    )
    parser.add_argument(
        "--format",
        choices=["sarek", "nf-resequencing-mem", "rnaseq", "mag"],
        default="sarek",
        help="Output format for the samplesheet (default: sarek)."
    )
    parser.add_argument(
        "--fastq_extension",
        type=str, default='fastq.gz',
        help="Pattern to search for FASTQ files (default: 'fastq.gz').",
    )
    parser.add_argument(
        "--prefix_pattern",
        type=str, default='_R',
        help=(
            "Pattern to be stripped out to determine sample names from files "
            "(default: '_R')."
        )
    )
    parser.add_argument(
        "--r2_suffix",
        type=str, default="2",
        help="Suffix number for R2 reads (default: '2'. ie: use '3' if R2 files are named R3)"
    )
    parser.add_argument(
        "--suffix_pattern",
        type=str, default=None,
        help=(
            "Suffix between read number and extension (default: %(default)s). "
            "Use '_001' for files like *_R1_001.fastq.gz"
        )
    )
    parser.add_argument(
        "--exclude_pattern",
        type=str, default=None,
        help="Pattern to exclude files from the search.",
    )
    # Use mutually exclusive group for Python 3.6 compatibility (BooleanOptionalAction requires 3.9+)
    samples_group = parser.add_mutually_exclusive_group()
    samples_group.add_argument(
        "--samples_as_dirs",
        dest="samples_as_dirs",
        action="store_true",
        help="Treat each directory as a sample (default)."
    )
    samples_group.add_argument(
        "--no-samples_as_dirs",
        dest="samples_as_dirs",
        action="store_false",
        help="Sample names are inferred from FASTQ filenames."
    )
    parser.set_defaults(samples_as_dirs=True)
    parser.add_argument(
        "--aliases",
        type=pathlib.Path,
        help="Path to a CSV file containing sample aliases.",
    )
    parser.add_argument(
        "--aliases_columns",
        type=str, nargs='+',
        default=["sampleName", "clientId"],
        help="Columns from the aliases CSV to define sample_names (from -> to). default: %(default)s.",
    )
    parser.add_argument(
        "--strandedness",
        type=str,
        choices=["auto", "unstranded", "forward", "reverse"],
        default="auto",
        help="Strandedness of the RNA-seq library (default: %(default)s).",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose output (DEBUG level logging).",
    )

    # read parameters
    args = parser.parse_args()

    # configure logging level based on verbose flag
    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(level=log_level, format='%(asctime)s - %(levelname)s - %(message)s')

    return args


def search_directories(path: pathlib.Path) -> List[pathlib.Path]:
    """
    Recursively search for directories in the given path.

    If no subdirectories are found, returns the path itself as a single-element list.
    This ensures that even leaf directories are processed.

    Args:
        path: The directory path to search

    Returns:
        List of pathlib.Path objects representing all directories found
    """

    if not path.is_dir():
        logger.error(f"Error: {path} is not a directory")
        return []

    directories = []
    for item in path.iterdir():
        if item.is_dir():
            directories.append(item)
            directories.extend(search_directories(item))

    return directories


def get_sample_name(
        item: pathlib.Path, fastq: pathlib.Path,
        args: argparse.Namespace, aliases: Dict) -> str:
    """
    Determine the sample name based on the provided arguments.

    Args:
        item: Directory path containing the FASTQ file
        fastq: Path to the FASTQ file
        args: Parsed command-line arguments
        aliases: Dictionary mapping original sample names to aliases

    Returns:
        The determined sample name (potentially aliased)
    """

    if args.samples_as_dirs:
        sample_name = item.name

    else:
        # Extract sample name by removing the prefix pattern and everything after it
        # e.g., "AGGG-SM-0007-RRBS-SM_R1_001.fastq.gz" -> "AGGG-SM-0007"
        match = re.match(rf"(.+?){re.escape(args.prefix_pattern)}\d", fastq.name)
        if match:
            sample_name = match.group(1)
        else:
            sample_name = fastq.stem

    # override sample name if aliases are provided
    if aliases and sample_name in aliases:
        sample_name = aliases[sample_name]

    return sample_name


def get_fastq_pairs(item: pathlib.Path, args: argparse.Namespace) -> Tuple[List[pathlib.Path], List[pathlib.Path]]:
    """
    Search for R1 and R2 FASTQ files in a directory using the specified patterns.

    Args:
        item: Directory path to search for FASTQ files
        args: Parsed command-line arguments containing pattern specifications

    Returns:
        Tuple of (r1_files, r2_files) - lists of sorted pathlib.Path objects
    """
    # build patterns for R1 and R2
    suffix = args.suffix_pattern if args.suffix_pattern else "*"
    r1_pattern = f"*{args.prefix_pattern}1{suffix}.{args.fastq_extension}"
    r2_pattern = f"*{args.prefix_pattern}{args.r2_suffix}{suffix}.{args.fastq_extension}"

    logger.debug(f"Searching for '{r1_pattern}' and '{r2_pattern}'")

    r1_files = sorted(item.glob(r1_pattern))
    logger.debug(f"Found {len(r1_files)} R1 files")

    r2_files = sorted(item.glob(r2_pattern))
    logger.debug(f"Found {len(r2_files)} R2 files")

    return r1_files, r2_files


def log_parameters_and_get_aliases(paths: List[pathlib.Path], args: argparse.Namespace) -> Dict:
    """
    Log configuration parameters and retrieve sample aliases.

    Args:
        paths: Directory paths being processed
        args: Parsed command-line arguments

    Returns:
        Dictionary of aliases (from sample name -> to sample name)
    """
    aliases = get_aliases(args)

    logger.debug(f"received paths: {paths}")
    logger.debug(f"using fastq_extension: {args.fastq_extension}")
    logger.debug(f"using prefix_pattern: {args.prefix_pattern}")
    logger.debug(f"using r2_suffix: {args.r2_suffix}")
    logger.debug(f"using samples_as_dirs: {args.samples_as_dirs}")
    logger.debug(f"using aliases: {aliases}")

    return aliases


def get_aliases(args: argparse.Namespace) -> Dict:
    """
    Read and parse sample aliases from CSV file if provided.

    Args:
        args: Parsed command-line arguments containing aliases file path and column names

    Returns:
        Dictionary mapping original sample names to their aliases
    """
    aliases = {}

    if args.aliases:
        alias_data = read_aliases(args.aliases)
        from_col, to_col = args.aliases_columns

        for row in alias_data:
            if from_col in row and to_col in row:
                aliases[row[from_col]] = row[to_col]
            else:
                logger.error(f"Alias columns '{from_col}' or '{to_col}' not found in aliases file.")
                sys.exit(1)

    return aliases


def read_aliases(path: pathlib.Path) -> List[Dict]:
    """
    Read a CSV file and return a list of dictionaries with sanitized column names.

    Column names are sanitized by removing leading '#' and replacing spaces with underscores.

    Args:
        path: Path to the CSV file containing aliases

    Returns:
        List of dictionaries, one per row, with sanitized column names as keys
    """

    sniffer = csv.Sniffer()

    with open(path, 'r') as handle:
        dialect = sniffer.sniff(handle.read(1024))
        handle.seek(0)
        reader = csv.DictReader(handle, dialect=dialect)
        data = list(reader)

    # Sanitize column names in each dict
    sanitized_data = []
    for row in data:
        sanitized_row = {k.lstrip('#').replace(' ', '_'): v for k, v in row.items()}
        sanitized_data.append(sanitized_row)

    return sanitized_data


def scan_for_fastq_files(paths: List[pathlib.Path], aliases: Dict, args: argparse.Namespace) -> Generator[Tuple[str, pathlib.Path, pathlib.Path], None, None]:
    """
    Scan the provided paths for FASTQ files and yield sample name, R1 path, and R2 path tuples.
    This function is a generator that yields tuples of (sample_name, fastq_1, fastq_2) for each valid sample found.
    """

    # include root paths and all subdirectories
    directories = list(paths)

    for path in paths:
        directories.extend(search_directories(path))

    logger.debug(f"Found {len(directories)} directories")

    for item in directories:
        logger.debug(f"Processing: {item}")

        if item.is_dir():
            # check for FASTQ files in directory
            r1_files, r2_files = get_fastq_pairs(item, args)

            if len(r1_files) == len(r2_files) and len(r1_files) >= 1:
                for i in range(len(r1_files)):
                    fastq_1 = r1_files[i]
                    fastq_2 = r2_files[i]

                    sample_name = get_sample_name(
                        item, fastq_1, args, aliases)

                    if args.exclude_pattern and args.exclude_pattern in sample_name:
                        logger.debug(f"Excluding sample {sample_name} due to exclude_pattern match.")
                        continue

                    yield (sample_name, fastq_1, fastq_2)

            else:
                logger.warning(f"Skipping {item}: found {len(r1_files)} R1 and {len(r2_files)} R2 files (must be equal and > 0)")

        else:
            logger.warning(f"Skipping {item}: not a directory")


def create_resequencing_mem_samplesheet(paths: List[pathlib.Path], aliases: Dict, args: argparse.Namespace) -> None:
    """
    Create a samplesheet in the nf-resequencing-mem format.

    Args:
        paths: Root directory path(s) containing sample folders
        aliases: Dictionary of aliases
        args: Parsed command-line arguments
    """

    # define header for nf-resequencing-mem format
    writer = csv.writer(sys.stdout, delimiter=',', lineterminator='\n')
    header = ['sample', 'fastq_1', 'fastq_2']
    writer.writerow(header)
    sys.stdout.flush()

    record_count = 0
    for sample_name, fastq_1, fastq_2 in scan_for_fastq_files(paths, aliases, args):
        writer.writerow([sample_name, fastq_1, fastq_2])
        sys.stdout.flush()
        record_count += 1

    logger.info(f"Wrote {record_count} records to samplesheet")


def create_sarek_samplesheet(paths: List[pathlib.Path], aliases: Dict, args: argparse.Namespace) -> None:
    """
    Create a samplesheet in the Sarek format.

    Sarek format includes patient, sample, lane, fastq_1, and fastq_2 columns.

    Args:
        paths: Root directory path(s) containing sample folders
        aliases: Dictionary of aliases
        args: Parsed command-line arguments
    """

    # define header for Sarek format
    writer = csv.writer(sys.stdout, delimiter=',', lineterminator='\n')
    header = ["patient", "sample", "lane", "fastq_1", "fastq_2"]
    writer.writerow(header)
    sys.stdout.flush()

    # Sarek requires additional columns with lane information
    lane_count = 0
    record_count = 0

    for sample_name, fastq_1, fastq_2 in scan_for_fastq_files(paths, aliases, args):
        lane_count += 1

        writer.writerow([
            sample_name,
            sample_name,
            f"lane_{lane_count}",
            fastq_1,
            fastq_2
        ])
        sys.stdout.flush()
        record_count += 1

    logger.info(f"Wrote {record_count} records to samplesheet")


def create_rnaseq_samplesheet(paths: List[pathlib.Path], aliases: Dict, args: argparse.Namespace) -> None:
    """
    Create a samplesheet in a simple RNA-seq format with sample, fastq_1, and fastq_2 columns.

    Args:
        paths: Root directory path(s) containing sample folders
        aliases: Dictionary of aliases
        args: Parsed command-line arguments
    """

    # define header for RNA-seq format
    writer = csv.writer(sys.stdout, delimiter=',', lineterminator='\n')
    header = ['sample', 'fastq_1', 'fastq_2', 'strandedness']
    writer.writerow(header)
    sys.stdout.flush()

    record_count = 0
    for sample_name, fastq_1, fastq_2 in scan_for_fastq_files(paths, aliases, args):
        writer.writerow([sample_name, fastq_1, fastq_2, args.strandedness])
        sys.stdout.flush()
        record_count += 1

    logger.info(f"Wrote {record_count} records to samplesheet")


def create_mag_samplesheet(paths: List[pathlib.Path], aliases: Dict, args: argparse.Namespace) -> None:
    """
    Create a samplesheet for nf-core/mag for illumina samples

    Args:
        paths: Root directory path(s) containing sample folders
        aliases: Dictionary of aliases
        args: Parsed command-line arguments
    """

    # TODO: deal with Nanopore input

    # define header for mag format
    writer = csv.writer(sys.stdout, delimiter=',', lineterminator='\n')
    header = ["sample", "group", "short_reads_1", "short_reads_2", "short_reads_platform"]
    writer.writerow(header)
    sys.stdout.flush()

    record_count = 0
    for sample_name, fastq_1, fastq_2 in scan_for_fastq_files(paths, aliases, args):
        writer.writerow([sample_name, record_count, fastq_1, fastq_2, "ILLUMINA"])
        sys.stdout.flush()
        record_count += 1

    logger.info(f"Wrote {record_count} records to samplesheet")


if __name__ == "__main__":
    # parse arguments and configure logging
    args = parse_args()
    paths = args.path

    for path in paths:
        if not path.is_dir():
            logger.error(f"Error: {path} is not a directory")
            sys.exit(1)

    logger.info("Starting samplesheet creation")
    aliases = log_parameters_and_get_aliases(paths, args)

    if args.format == "nf-resequencing-mem":
        logger.debug("Creating nf-resequencing-mem samplesheet")
        create_resequencing_mem_samplesheet(paths, aliases, args)

    elif args.format == "sarek":
        logger.debug("Creating Sarek samplesheet")
        create_sarek_samplesheet(paths, aliases, args)

    elif args.format == "rnaseq":
        logger.debug("Creating RNA-seq samplesheet")
        create_rnaseq_samplesheet(paths, aliases, args)

    elif args.format == "mag":
        logger.debug("Creating mag samplesheet")
        create_mag_samplesheet(paths, aliases, args)

    else:
        logger.error(f"Unknown format: {args.format}")
        sys.exit(1)

    logger.info("Samplesheet creation completed")
