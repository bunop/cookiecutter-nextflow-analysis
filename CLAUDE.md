# CLAUDE.md

Keep your replies extremely concise and focus on conveying the key information. No unnecessary fluff, no long code snippets.

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

A [cookiecutter](https://cookiecutter.readthedocs.io/) template that scaffolds a reproducible Nextflow analysis project directory. There is no application code to build/test/run — the repo's only "product" is the generated project tree, and the only way to validate a change is to actually generate a project and inspect the output.

## Commands

Generate a project from the template (run from the repo root, or point cookiecutter at this path):

```bash
cookiecutter .
```

This prompts interactively for the values in `cookiecutter.json` (`project_slug`, `include_data`, `project_type`, `nextflow_as_a_job`, `with_docker`). To test non-interactively / for a specific combination:

```bash
cookiecutter . --no-input project_type=wf-basecalling with_docker=true
```

There are no linters, tests, or CI configured. When changing a `.jinja` template or any file under `{{cookiecutter.project_slug}}/` or `templates/`, verify by generating a project with each relevant `project_type` (at minimum `unknown` and `wf-basecalling`, since those exercise the most divergent branches) and reading the rendered output.

To check Jinja whitespace/newline behavior in isolation without a full generation, render the template string directly with `jinja2.Environment(keep_trailing_newline=True)` (this matches cookiecutter's `StrictEnvironment` defaults — no `trim_blocks`/`lstrip_blocks`).

## Architecture

- `cookiecutter.json` — defines the prompts/choices. `project_type` is the main branch point (`unknown`, `wf-basecalling`, `nf-core/methylseq`, `nf-core/methylong`, `nf-core/rnaseq`, `nf-core/smrnaseq`); most templates `{% if/elif %}` on this value.
- `{{cookiecutter.project_slug}}/` — the actual template for the generated project (README, `conf/`, `data/`, `scripts/launch.sh`). Files here can be `.jinja`-rendered even without the extension (cookiecutter renders all files by default).
- `{{cookiecutter.project_slug}}/.claude/skills/` — Claude Code skills shipped with every generated project (rendered by Jinja like any other file, so they can branch on `project_type`). `split-samplesheet` drives `scripts/make_samplesheet.py` + `scripts/divide_samples_in_batches.py` (seqkit stats → samplesheet → size-balanced batches → test set → README → commit). Test a skill end-to-end by generating a project with fake gzipped FASTQ in `data/` and running `claude -p "/<skill> ..."` inside it.
- `templates/` — **not** copied into the generated project directly. It's added as an extra Jinja `{% include %}` search path (cookiecutter adds the repo's `templates/` dir to the loader search path automatically), so files here are pulled in piecemeal by `{% include "..." %}` tags from files under `{{cookiecutter.project_slug}}/`. Examples: `templates/README/basecalling.jinja` is included by the README when `project_type == "wf-basecalling"`; `templates/cineca.sh`, `templates/wf-basecalling.sh`, `templates/methylseq.sh`, etc. are included by `scripts/launch.sh` to assemble the SLURM job script per pipeline.
- `hooks/post_gen_project.py` — runs after generation. It:
  - removes `data/` if `include_data` is false,
  - removes `scripts/launch.sh` if `nextflow_as_a_job` is false,
  - writes `conf/params.json` from a hardcoded per-`project_type` dict (`json_params` in the hook), falling back to `unknown_params`,
  - copies an extra helper script into `scripts/` for specific project types (`parse_ont_report.py` for `wf-basecalling`, `bedMethyl2cov.py` for `nf-core/methylong`) — these scripts live in `templates/` and are copied with `shutil.copy`, not rendered as Jinja.
  - When adding a new `project_type`, the default params and any extra copied script need to be added here, not just in the templates.

## Jinja whitespace conventions

Cookiecutter's Jinja env keeps the trailing newline but does **not** set `trim_blocks`/`lstrip_blocks`, so every `{% tag %}` on its own line leaves a newline in the output unless stripped with `-`. The convention used across this repo's templates:

- Use `{% if ... -%}` (no strip before, strip after) when a blank line *before* the tag should be preserved but the tag's own line break should not appear in the output.
- Use `{%- elif/else -%}` and `{%- endif %}` (or `{%- endif -%}`) for the inner/closing tags so they never leave a stray blank line.

See `{{cookiecutter.project_slug}}/README.md` and `templates/README/basecalling.jinja` for examples of this pattern in both directions (with/without docker, per-`project_type` branches).
