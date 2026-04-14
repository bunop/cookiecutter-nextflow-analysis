#!/bin/bash
#SBATCH --nodes=1
#SBATCH --ntasks-per-node=1
#SBATCH --cpus-per-task=2
#SBATCH --time=<time limit>
#SBATCH --mem=16G
#SBATCH --output=%x-%j.out              # using job_name + job_id as log file
#SBATCH --job-name={{ cookiecutter.project_type.split('/')[1] }}
{% include "cineca.sh" %}

# set the path of institution-specific configuration files
export CUSTOM_CONFIG_BASE=${WORK}/nf-configs
{% if cookiecutter.project_type == "nf-core/methylseq" %}
{% include "methylseq.sh" %}
{% elif cookiecutter.project_type == "nf-core/methylong" %}
{% include "methylong.sh" %}
{% elif cookiecutter.project_type == "nf-core/rnaseq" %}
{% include "rnaseq.sh" %}
{% endif %}
