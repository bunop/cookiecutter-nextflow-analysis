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

## Claude Code skills

Generated projects ship with [Claude Code](https://claude.com/claude-code) skills in `.claude/skills/`:

- `/split-samplesheet`: computes `seqkit stats`, builds the samplesheet, splits it into size-balanced batches, creates a test samplesheet/params, documents the steps in the README and commits.
- `/aws-costs` (only with `use_aws_batch`): reads the cost of a run on AWS Batch with `scripts/aws_costs.py` (Cost Explorer, CloudTrail, Batch), writes CSV files in `docs/aws-costs/` and forecasts the cost of the full dataset.
- `/slurm-job`: writes a SLURM job script in `scripts/` (or fills the placeholders of `scripts/launch.sh`) for the detected cluster (CINECA/CNR), or runs the command locally; always asks before launching.

## Contributing

Contributions welcome! Please submit issues and pull requests.

## License

MIT License
