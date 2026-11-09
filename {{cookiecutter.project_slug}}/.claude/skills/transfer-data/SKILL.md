---
name: transfer-data
description: Write in the README (and show to the user) the rsync commands to copy raw data to CINECA ($SCRATCH) or results back to the local server (core), and the md5sum integrity check. It never runs the transfers. Use when the user asks how to upload/download data or results to/from CINECA, or to verify a transfer against an md5 file.
---

# Transfer data to/from CINECA

Goal: reproducible `rsync` commands with the right permissions and excludes,
plus an md5 check of the copied raw data, **written in the README and shown to
the user, who runs them**. Transfers are long and need the user's CINECA ssh
key: never run `rsync`, `ssh` or `ssh-add` yourself.

## 0. Ask what is missing

One AskUserQuestion with all open points: direction (upload raw data /
download results / md5 check), source and destination paths, CINECA user and
group (`--chown`). Host is usually `data.g100.cineca.it`; scratch is
`/g100_scratch/userexternal/<user>/`, work is `/g100_work/<group>/`.
Nothing is hardcoded: take them from the README or `~/.ssh/config` if present.

Remind the user that the CINECA key must be loaded in the ssh agent of the
machine that runs `rsync` (`ssh-add ~/.ssh/<cineca_key>`); creating the key is up to them.

## 1. Upload raw data to `$SCRATCH` (run from the local server)

```bash
rsync -varPe ssh --chmod=Du=rwx,Dg=rwxs,Do=rx,Fu=rw,Fg=rw,Fo=r \
    --chown <user>:<group> [--exclude="<folder>/"] \
    <source folder> <user>@data.g100.cineca.it:/g100_scratch/userexternal/<user>/
```

`--chmod`/`--chown` need rsync >= 3.1.0 (`rsync --version`); the SGID bit
(`Dg=rwxs`) keeps the group on new files. No trailing `/` on the source copies
the folder itself, with it only its content.

## 2. Check integrity (on CINECA)

Needs the md5 file shipped with the data. It is CPU bound: **not on the login
node**, use `/slurm-job` (script `scripts/check_md5.sh`, 4 cpus, `g100_all_serial`
partition, a few hours) running:

```bash
DATADIR=<folder with the data and the md5 file>
parallel --joblog $DATADIR/parallel.log -j${SLURM_CPUS_PER_TASK:-1} \
    'echo {} | md5sum -c' < <md5 file> | tee $DATADIR/checksum_output.txt
```

(paths inside the md5 file are relative: run it from the folder they refer to).
Then check, no output means all `OK`:

```bash
grep -v ': OK$' $DATADIR/checksum_output.txt
```

Show any `FAILED` / `FAILED open or read` file to the user; re-run the upload
of those files only.

## 3. Download results to the local server (run on core)

```bash
rsync -varPLue ssh --cvs-exclude --no-group \
    --exclude=data{% if cookiecutter.project_type in ["nf-core/methylseq", "nf-core/methylong"] %} --exclude=alignments{% endif %} --exclude=.nextflow \
    <user>@data.g100.cineca.it:/g100_work/<group>/<project>/ <local project folder>/
```

- `-L` follows symlinks: results are often links into another folder, so
  `data` must be excluded or the raw data is copied too;
- `--cvs-exclude` skips `.git/` (the project is managed with git);
- `.nextflow` holds temporary files and lockfiles{% if cookiecutter.project_type in ["nf-core/methylseq", "nf-core/methylong"] %}; `alignments` is too large{% endif %};
- `-u` skips files newer in the destination; `--no-group` gives new files the
  group of the destination folder (it should have the SGID bit).

## 4. Write the README

Put the commands, with the user's real values, in `README.md` (sections "Copy
raw data to CINECA", "Check file integrity", "Copy results"), with the key
reminder as a note. Tell the user to try each `rsync` with `-n` (`--dry-run`)
first and to run it in `tmux`/`screen`. Then show `git status` and ask before
committing. The md5 check is the only thing that may become a job script
(`/slurm-job`), and only if the user asks.
