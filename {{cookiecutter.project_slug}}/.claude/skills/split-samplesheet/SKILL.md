---
name: split-samplesheet
description: Prepare batched inputs for this Nextflow analysis - compute seqkit stats on the raw FASTQ, build the samplesheet, split it into size-balanced batches, create a small test samplesheet/params, document every step in the README and leave a clean git commit. Use when the user asks to split samples in batches, prepare samplesheets, or set up a test run.
---

# Split samplesheet in batches

Goal: starting from the raw data, produce one samplesheet per batch, a test
samplesheet + params, and a README section that lets anyone reproduce them.
Project type: `{{ cookiecutter.project_type }}`.

Work step by step. Start from what already exists; **ask the user only for
what is missing** (use one AskUserQuestion with all the open points, not many).
Never overwrite `conf/samplesheet.csv` or `conf/params.json`: in the end there
will be one samplesheet (and params) per batch.

## 0. Survey

- Read `README.md`, `conf/`, `scripts/`, `git status`, and look for existing
  `seq_stats.*` / `conf/samplesheet_*.csv` (skip steps already done, but say so).
- Find the raw data: `data/` (often a symlink or ignored by git) or a path
  given by the user. Look at a few file names (`find <path> -name '*.f*q.gz' | head`)
  to infer R1/R2 naming and whether samples are one per directory.
- Collect what is missing, proposing these defaults:
  - number of batches: **4** (rule of thumb: ~250 GB of fastq per batch,
    check with `du -shL <data path>`);
  - seqkit from the Singularity cache `/home/core/nxf_singularity_cache/`
    (`ls /home/core/nxf_singularity_cache/ | grep -i seqkit`) or from conda;
  - run seqkit stats on `node2` to bypass the NFS network switch (ask how:
    `srun -w node2 -c 4 ...` or `ssh node2`), or locally;
  - test params target: AWS (`conf/params-test-aws.json`).

## 1. Statistics

seqkit stats is disk bound and does not scale with threads: keep `-j 4`.
Use absolute paths, so stats can be joined to the samplesheet:

```bash
find $(realpath <data path>) -name '*.fastq.gz' | sort | \
    xargs seqkit stats -j 4 -T > seq_stats.tsv
```

(prefix `seqkit` with `singularity exec <image.img>` and/or the node command
chosen above).
It may take hours: run it in background and check the output is complete
(one row per fastq file) before moving on.

## 2. Samplesheet

Use `scripts/make_samplesheet.py` (`--help` for all options) on the data folder:

{% if cookiecutter.project_type == "nf-core/rnaseq" -%}
```bash
python3 scripts/make_samplesheet.py --path <data path> --format rnaseq > conf/samplesheet_all.csv
```
{%- elif cookiecutter.project_type in ["nf-core/methylseq", "nf-core/smrnaseq"] -%}
```bash
python3 scripts/make_samplesheet.py --path <data path> --format nf-resequencing-mem > conf/samplesheet_all.csv
```

The output has `sample,fastq_1,fastq_2` columns: adapt it to the header
expected by `{{ cookiecutter.project_type }}` (see `conf/samplesheet.csv`).
{%- else -%}
```bash
python3 scripts/make_samplesheet.py --path <data path> --format <sarek|nf-resequencing-mem|rnaseq> > conf/samplesheet_all.csv
```

Pick the format matching the header in `conf/samplesheet.csv`.
{%- endif %}

- Pass `--path $(realpath <data path>)` so the samplesheet has absolute paths
  (for AWS runs, paths will need to point to S3: ask the user).
- Tune `--prefix_pattern`, `--suffix_pattern`, `--r2_suffix`,
  `--no-samples_as_dirs`, `--exclude_pattern`, `--aliases` to the file names.
- If the options are not enough, edit the script: it is tracked in git, so
  modify it as needed (and mention it in the README).
- Check: number of rows vs number of fastq pairs, no duplicated sample names,
  all paths exist.

## 3. Split in batches

```bash
python3 scripts/divide_samples_in_batches.py \
    --samplesheet conf/samplesheet_all.csv --stats seq_stats.tsv \
    --num_batches 4 -o conf/samplesheet
```

It sums the `sum_len` (bases) of all files of a sample (`--column num_seqs`
to use reads), sorts samples by size and distributes them round robin, writing
`conf/samplesheet_aa.csv`, `conf/samplesheet_ab.csv`, ... (samples sorted by
size, descending). It must end with "All samples were written exactly once":
otherwise investigate. Report the per-batch summary to the user.

## 4. Test files

From one batch take the **first 3 and the last 3 samples** (biggest and
smallest: verify the ordering against `seq_stats.tsv`, don't trust it blindly;
if the batch has 6 samples or fewer, tell the user the test set is the whole
batch) and write, keeping the header and all rows (lanes) of those samples:

- `conf/samplesheet-test.csv`
- `conf/params-test-aws.json`: a copy of `conf/params.json` with `input`
  pointing to `conf/samplesheet-test.csv` and a test output folder; ask the
  user for values still left as `<placeholder>` (e.g. S3 paths).

Do not write in `conf/samplesheet.csv` or `conf/params.json`.

## 5. Documentation

Add a section to `README.md` (e.g. "## Input preparation") describing what was
done to obtain these files: the exact commands (seqkit, make_samplesheet,
divide_samples_in_batches, how the test set was chosen), any change made to
the scripts, number of samples and size of each batch.

## 6. Git

- Remove the template files no longer needed (e.g. `conf/samplesheet.csv` if
  only the per-batch files are used, `.gitkeep` files in non-empty folders,
  placeholder text in the README): list them and ask before deleting.
- `seq_stats.tsv` is small: commit it.
- Show `git status` and the commit message, ask for confirmation, then commit
  everything. The working tree must be clean at the end (`git status`).
