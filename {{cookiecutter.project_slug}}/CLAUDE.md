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

## Running tools (seqkit, csvkit, bcftools, ...)

Use the first that works; if none does, ask the user.

1. **In `PATH`**: `command -v <tool>`.
2. **Singularity/Apptainer image** in the Nextflow cache:
   `ls "$NXF_SINGULARITY_CACHEDIR" | grep -i <tool>` (names like
   `depot.galaxyproject.org-singularity-bcftools-1.18--h8b25389_0.img`; with
   several versions use the one the user asks for, else the newest and say so). Run it with

   ```bash
   singularity exec --bind "$PWD" <image> <tool> <args>
   ```

   Add to `--bind` the targets of the `data/` symlinks (`readlink -f data`).
   Never pull an image without asking (network and disk): if missing, propose
   `singularity pull "$NXF_SINGULARITY_CACHEDIR/<name>.img" docker://quay.io/biocontainers/<tool>:<version>--<build>`.
3. **conda/micromamba env** named after the tool
   (`micromamba env list | grep -i <tool>`, or `conda env list`): from the shell use
   `micromamba run -n <env> <command>` (wrap a whole pipeline in `bash -c '...'`);
   inside a script activate the env (see `/slurm-job`), as `conda run` does not
   forward stdin in a pipe.

Record in the script and in the README how the tool was run (image name, or
env) and its version (`<tool> --version`), for reproducibility. Names of envs
and images specific to the user's machine go in `CLAUDE.local.md`, not here.

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
