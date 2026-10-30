---
name: aws-costs
description: Read what a Nextflow run on AWS Batch cost (Cost Explorer, CloudTrail, Batch) with scripts/aws_costs.py, write the CSV files in docs/aws-costs/, and use CPU-hours per process to forecast the cost of the full dataset from a test run. Use when the user asks how much a run cost, to estimate the cost of the whole analysis, or to compare Spot/on-demand and memory settings by cost.
---

# AWS costs

Goal: CSV files in `docs/aws-costs/` (tracked in git) that say what a run on
AWS Batch cost and where, a forecast for the full dataset, and a note in
`docs/aws-costs.md` and the README. Confirmation rule: see `CLAUDE.md`.

Work step by step. Start from what already exists (`docs/aws-costs*`,
`conf/*.config`, `git log`); **ask the user only for what is missing** (one
AskUserQuestion with all the open points, not many).

## 0. Can we read it now?

Time limits of the sources: **Batch keeps finished jobs 7 days**, CloudTrail 90
days, Cost Explorer lags up to 24 h (a settled value after 24-48 h; its end
date is exclusive). So read the jobs soon after the run; re-run later for the
final costs (the script overwrites the CSVs).

IAM permissions of the user: `ce:GetCostAndUsage` (always called in
`us-east-1`), `cloudtrail:LookupEvents` and `batch:ListJobs`/`batch:DescribeJobs`
in the Batch region. If a call is denied, report which one and stop.

## 1. Ask what is missing

Take these from the project when possible, otherwise ask:

- AWS profile: `aws.profile` in `conf/*.config`, else `$AWS_PROFILE`.
- Region and job queue(s): `aws.region` and `process.queue` in the config of the
  `awsbatch` profile (`nextflow config -profile awsbatch -flat | grep -E 'queue|region'`).
  Pass every queue that ran jobs (e.g. Spot and on-demand), one `--queue` each.
- Period: `--start` (first day, UTC) and `--end` (day after the last, exclusive);
  take them from the dates of the run in `.nextflow.log`/the README.
- `--until YYYY-MM-DDTHH:MM:SSZ` if other tests ran later in the same queue
  and must be left out.
- Instance types that are not Batch jobs (e.g. a launcher VM): `--exclude-types`.

## 2. Run the script

Check the AWS CLI works (`aws sts get-caller-identity --profile <profile>`), then
confirm and run from the project root:

```bash
python3 scripts/aws_costs.py --profile <profile> --region <region> --queue <queue> \
    --start <YYYY-MM-DD> --end <YYYY-MM-DD> [--until ...] [--classes conf/aws_cost_classes.json]
```

Outputs in `docs/aws-costs/` (`--outdir`): `cost_by_day_service.csv`,
`cost_by_instance_type.csv` (EC2 hours per type), `instances.csv` (life of every
instance, from CloudTrail), `jobs.csv` (one row per Batch attempt, with
`status_reason` of the failed ones), `allocation_window.csv` (vCPU-hours of the
instances vs reserved by the jobs: low `reserved_share` = paid but idle),
`cost_by_process.csv`, `cost_by_class.csv`.

- The cost per process is a **model** (hours × share of a reference instance ×
  its price), not a measure: set `--ref-vcpus`, `--ref-memory-gib`, `--ref-price`
  to the instance type that dominates `cost_by_instance_type.csv`. Compare the
  model total with the EC2 bill (printed at the end).
- By default each process is its own class. For a readable report write
  `conf/aws_cost_classes.json`, a list of `[label, regex]` (first match wins, e.g.
  `[["Assembly", "ASSEMBL"], ["Mapping", "BWA|BOWTIE|MINIMAP"]]`), built from the
  process names in `cost_by_process.csv`, and pass it with `--classes`.
- `--raw-dir <dir>` keeps the raw AWS answers, `--cache` re-reads them without calling AWS.
- Jobs that were retried or lost (Spot reclaim) appear as extra attempts in
  `jobs.csv`: their hours are part of the cost.

## 3. Forecast the full dataset

Don't divide the total by the number of samples of the test: processes scale
differently (per-sample steps ×N, cohort-wide steps and database preparation ×1,
some steps grow more than linearly with the read depth). Instead:

1. take CPU-hours and `peak_rss` per process from the Nextflow `execution_trace`
   (`results*/pipeline_info/`) and `cost_by_process.csv`;
2. per class choose a factor: per-sample ×(samples / test samples) × (reads ratio),
   fixed steps ×1; state the assumption;
3. give a range (low/high factor) and the price per vCPU-hour from the test.

A test on a fraction of the reads under-estimates steps that depend on depth:
say so, and recheck the forecast on a larger pilot if there is one.

## 4. Cost levers (only suggest, don't change the config unasked)

- `reserved_share` low → memory/CPU requests too high for the instance sizes, or
  a few long tasks keeping big instances alive;
- memory requests from `peak_rss` of the trace; never below the minimum the
  project already uses;
- many lost attempts on long processes → retry them on an on-demand queue;
- databases and work dir on S3: clean `work/` after collecting the results.

## 5. Documentation and git

- Write `docs/aws-costs.md`: period, queues, total EC2 cost and how settled it is
  (Estimated flag), table by class, allocation, forecast with its assumptions, and
  the exact command to repeat it. Add a short pointer in `README.md`.
- Show `git status` and the commit message, ask for confirmation, then commit the
  CSVs, the doc and `conf/aws_cost_classes.json`. Never commit raw AWS answers.
