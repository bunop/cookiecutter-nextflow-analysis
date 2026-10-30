# CLAUDE.md

Nextflow analysis project (`{{ cookiecutter.project_type }}`). Run every command
from the project root and keep paths relative to it: raw data in `data/`
(often a symlink), configuration in `conf/`, scripts in `scripts/`, job logs in `logs/`.

## Where heavy commands run

- **CINECA** (`$PRJ_ACCOUNT` defined or `~/.ch_acc.def` exists): login nodes
  kill any command after 10 minutes of CPU time. Nextflow, seqkit, helper
  scripts and long `du`/`find` on big folders must run as SLURM jobs: use `/slurm-job`.
- **CNR** (`sbatch` available, no CINECA account): Nextflow runs on the login
  node; long commands can run in background or as a job (`/slurm-job`).
- **Local**: run long commands in background.

Never launch a job, a pipeline or a long command without first summarizing
what will run and getting an explicit confirmation.

## Folder sizes

`du` time grows with the number of files, not the size: seconds for `data/`,
possibly tens of minutes for `work/` or `results/`.

- Follow symlinks (`du -shL`) for `data/` (often a symlink) and `results/`
  (often only links into `work/`). Not for `work/`: task folders link their
  inputs, so `-L` would count the raw data again; use plain `du -sh`.
- Run it in background and save the output, e.g.
  `mkdir -p logs && du -hL --max-depth=1 results/ > logs/du_results.txt`; reuse that file if recent.
- On CINECA, `du` on `work/` or `results/` goes in a job (`/slurm-job`).
{%- if cookiecutter.use_aws_batch %}

## AWS Batch

- Use the profile of `aws.profile` in `conf/*.config` (`export AWS_PROFILE=<profile>`);
  the Batch environment is usually Spot, so lost tasks are retried.
- Run one batch of samples at a time; before `aws s3 rm` on a shared work
  directory make sure no other run uses it, and ask for confirmation.
- Run costs and their forecast: `/aws-costs` (Batch keeps jobs only 7 days: read them soon after the run).
{%- endif %}
