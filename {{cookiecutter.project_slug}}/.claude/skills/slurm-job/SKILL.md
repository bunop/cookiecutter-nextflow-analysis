---
name: slurm-job
description: Write (or fix) a SLURM job script in scripts/ to run a long command of this project (seqkit, a helper script in scripts/, nextflow) on the cluster, or run it locally in background when SLURM is not available. Also fills the placeholders (<account>, <time limit>) of an existing script like scripts/launch.sh. Use when the user asks to run something as a job, to create/customize a slurm script, or when a command is too long for the login node.
---

# SLURM job

Goal: a script `scripts/<name>.sh`, tracked in git, that runs a command of this
project on the right resources, plus a README note on how it was launched.
Where commands may run and the confirmation rule: see `CLAUDE.md`.

Work step by step. Start from what already exists; **ask the user only for
what is missing** (use one AskUserQuestion with all the open points, not many).

## 0. Where are we?

```bash
command -v sbatch; echo "SLURM_JOB_ID=${SLURM_JOB_ID:-}"; echo "PRJ_ACCOUNT=${PRJ_ACCOUNT:-}"; ls ~/.ch_acc.def
```

- **CINECA**: account, partition and QoS are required.
- **CNR**: no account/quota needed, the default partition is the long one (no
  time limit, don't specify it); there is also a test partition with 4h
  walltime (`sinfo -s` for its name).
- **Local / test**: run the script with `bash` in background.
- `SLURM_JOB_ID` set: we are already inside an allocation, run directly.

Also look at `scripts/*.sh`, `README.md` and `git status`: reuse what exists.

## 1. How to run the tool

Find the tool as described in `CLAUDE.md` ("Running tools": `PATH`, Singularity
image, conda/micromamba env). In the script:

- Singularity: `singularity exec --bind "$PWD" <image> <tool> ...`; if the data
  is elsewhere (e.g. `$SCRATCH`, targets of the `data/` symlinks) export
  `SINGULARITY_BINDPATH="$PWD,<other path>"` before it;
- conda/micromamba env: activate it with

```bash
if command -v conda &> /dev/null; then
    eval "$(conda shell.bash hook)"
    conda activate <env>
elif command -v micromamba &> /dev/null; then
    eval "$(micromamba shell hook -s bash)"
    micromamba activate <env>
else
    echo "Neither conda nor micromamba found in PATH."
    exit 1
fi
```

Activate the env in the script (as above) instead of `conda run`, which does
not forward stdin when the command is in a pipe.

## 2. Ask what is missing

Job name, command(s), input → output, resources. Default resources:

| command | cpus | mem | time |
|---|---|---|---|
| `seqkit stats` (disk bound, `-j 4` is enough) | 4 | 16G | 12:00:00 |
| `scripts/bedMethyl2cov.py` (single thread) | 1 | 16G | 16:00:00 |
| nextflow head job (`scripts/launch.sh`) | 2 | 16G | the whole pipeline |
| anything else | 1 | 8G | ask |

**Account (CINECA only)** is written in the script, so the project is bound to it:

1. if another `scripts/*.sh` already has a real `--account=`, reuse it (one account per project);
2. otherwise propose `$PRJ_ACCOUNT` (or the content of `~/.ch_acc.def`) as
   default, together with the accounts listed by
   `sacctmgr -nP show assoc user=$USER format=account | sort -u`, and ask which one to use.

## 3. Write `scripts/<name>.sh`

```bash
#!/bin/bash
#SBATCH --nodes=1
#SBATCH --ntasks-per-node=1
#SBATCH --cpus-per-task=<cpus>
#SBATCH --time=<time>
#SBATCH --mem=<mem>
#SBATCH --output=logs/%x-%j.out         # using job_name + job_id as log file
#SBATCH --job-name=<name>
set -euo pipefail

if [ ! -e <output> ]; then
    <command>
fi
```

- CINECA: add after `--job-name`
  - `#SBATCH --account=<account>`
  - `#SBATCH --partition=g100_usr_prod`
  - `#SBATCH --qos=normal` if time ≤ 24h, `#SBATCH --qos=g100_qos_lprod` if time > 24h.
- CNR: no account/qos; `--partition=<test partition>` only if time ≤ 4h and the user wants it;
  `--nodelist=<node>` only if the user asks to pin the job (e.g. the node that mounts the data).
- Paths are **relative** to the project root (the job is submitted from there);
  pass threads as `$SLURM_CPUS_PER_TASK` (`${SLURM_CPUS_PER_TASK:-1}` if it may run without SLURM).
- The `if [ ! -e <output> ]` guard makes the job safe to resubmit: one guard per step.
- Check: `bash -n scripts/<name>.sh`, `mkdir -p logs` (SLURM does not create it and
  the job would fail silently; `logs/` is git-ignored), on a cluster `sbatch --test-only scripts/<name>.sh`
  (validates account/partition/resources without submitting).

### Fixing an existing script (e.g. `scripts/launch.sh`)

Replace only the placeholders (`<account>`, `<time limit>`, ...) and what the
user asks, following the same rules: account as above, QoS from the time
limit; on CNR remove the CINECA `--account`/`--partition`/`--qos` lines.
Don't touch the rest of the script.

## 4. Confirm, then launch

Before running **anything** (`sbatch`, `bash`, `nohup`), summarize:
script written/modified, detected site, account, partition/QoS,
cpus/mem/time, exact command, input → output, where the logs go.
Then ask with AskUserQuestion: submit / run locally in background / don't run.
Only after an explicit yes:

- cluster: `sbatch scripts/<name>.sh` (report the job id; `squeue --me` to follow it);
- local: `nohup bash scripts/<name>.sh > logs/<name>.log 2>&1 &`.

## 5. Documentation and git

- Add to `README.md` (in the section of the step it belongs to) how the job
  was launched: `sbatch scripts/<name>.sh`, resources, what it produces.
- Show `git status` and the commit message, ask for confirmation, then commit
  the script and the README. Never commit `logs/`.
