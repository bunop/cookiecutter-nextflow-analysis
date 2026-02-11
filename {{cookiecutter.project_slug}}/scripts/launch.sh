#!/bin/bash
#SBATCH --nodes=1
#SBATCH --ntasks-per-node=1
#SBATCH --cpus-per-task=2
#SBATCH --time=<time limit>
#SBATCH --mem=16G
#SBATCH --output=%x-%j.out              # using job_name + job_id as log file
#SBATCH --job-name=methylseq
#SBATCH --account=<your account name>
#SBATCH --partition=<partition name>
#SBATCH --qos=<qos name>

# set the path of institution-specific configuration files
export CUSTOM_CONFIG_BASE=${WORK}/nf-configs
{% if cookiecutter.project_type == "nf-core/methylseq" %}
{% include "launch-methylseq.sh" %}
{% endif %}
