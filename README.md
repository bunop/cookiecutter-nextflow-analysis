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
├── README.md
├── conf
├── data
└── scripts
```

## Usage

Customize `cookiecutter.json` with your project parameters, then generate a new project structure.

## Contributing

Contributions welcome! Please submit issues and pull requests.

## License

MIT License
