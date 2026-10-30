# cookiecutter-nextflow-analysis

A cookiecutter template for creating reproducible data analysis with nextflow.

## Features

- Pre-configured Nextflow project structure
- Docker/Singularity container support
- Modular workflow organization
- Configuration management
- Documentation templates

## Quick Start

```bash
cookiecutter https://github.com/bunop/cookiecutter-nextflow-analysis.git
```

## Requirements

- Python 3.7+
- Cookiecutter

## Project Structure

```
{{cookiecutter.project_slug}}/
├── .claude/skills   # Claude Code skills (e.g. /split-samplesheet, /slurm-job)
├── CLAUDE.md        # Claude Code rules: where heavy commands run (CINECA/CNR/local), du
├── README.md
├── conf
├── data
└── scripts
```

## Usage

Customize `cookiecutter.json` with your project parameters, then generate a new project structure.

## Updating existing projects

Use [cruft](https://cruft.github.io/cruft/) (`pipx install cruft`) to pull template changes into a generated project. It stores the template commit and your answers in `.cruft.json` and applies the diff between the old and new template versions as a patch, keeping your local edits.

New projects: generate with `cruft create <path-or-url-of-this-repo>` instead of `cookiecutter`.

Projects already generated with `cookiecutter`: inside the project, run `cruft link <path-or-url> --checkout <commit>` (the template commit it was generated from, or the closest one by date), then `git add .cruft.json && git commit`. `link` asks for the cookiecutter answers; give the same ones used originally.

Then, from a clean git working tree:

```bash
cruft check    # is the template ahead?
cruft diff     # preview the changes
cruft update   # apply them; resolve any *.rej files
```

Review with `git diff --staged` and commit. Files rewritten by the post-generation hook (e.g. `conf/params.json`) are the likeliest to conflict.

## Claude Code skills

Generated projects ship with [Claude Code](https://claude.com/claude-code) skills in `.claude/skills/`:

- `/split-samplesheet`: computes `seqkit stats`, builds the samplesheet, splits it into size-balanced batches, creates a test samplesheet/params, documents the steps in the README and commits.
- `/aws-costs` (only with `use_aws_batch`): reads the cost of a run on AWS Batch with `scripts/aws_costs.py` (Cost Explorer, CloudTrail, Batch), writes CSV files in `docs/aws-costs/` and forecasts the cost of the full dataset.
- `/clean-csv`: removes the UTF-8 BOM and the completely empty rows and columns from a CSV (e.g. an Excel export) with `scripts/clean_csv.py`.
- `/slurm-job`: writes a SLURM job script in `scripts/` (or fills the placeholders of `scripts/launch.sh`) for the detected cluster (CINECA/CNR), or runs the command locally; always asks before launching.

## Contributing

Contributions welcome! Please submit issues and pull requests.

## License

MIT License
