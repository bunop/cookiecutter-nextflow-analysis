#!/bin/bash
#SBATCH --nodes=1
#SBATCH --ntasks-per-node=1
#SBATCH --cpus-per-task=2
#SBATCH --time=<time limit>
#SBATCH --mem=16G
#SBATCH --signal=B:TERM@1800            # SIGTERM to the batch shell 30 min before the time limit (use --time above 30 min)
#SBATCH --output=logs/%x-%j.out         # using job_name + job_id as log file
#SBATCH --job-name={{ cookiecutter.project_type.split('/')[-1] }}-{{ cookiecutter.project_slug }}
{% include "cineca.sh" %}

# set the path of institution-specific configuration files
export CUSTOM_CONFIG_BASE=${WORK}/nf-configs

# forward SIGTERM (SLURM time warning / scancel) to nextflow, so it stops its jobs and releases the lock
nextflow() { command nextflow "$@" & NF_PID=$!; wait $NF_PID; rc=$?; [ $rc -gt 128 ] && kill -0 $NF_PID 2>/dev/null && { wait $NF_PID; rc=$?; }; return $rc; }
trap 'kill -TERM $NF_PID 2>/dev/null || exit 143' TERM
{% if cookiecutter.project_type == "wf-basecalling" %}
{% include "wf-basecalling.sh" %}
{% elif cookiecutter.project_type == "nf-core/methylseq" %}
{% include "methylseq.sh" %}
{% elif cookiecutter.project_type == "nf-core/methylong" %}
{% include "methylong.sh" %}
{% elif cookiecutter.project_type == "nf-core/rnaseq" %}
{% include "rnaseq.sh" %}
{% elif cookiecutter.project_type == "nf-core/smrnaseq" %}
{% include "smrnaseq.sh" %}
{% endif %}
