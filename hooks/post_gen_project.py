import os
import json
import shutil

# get the values from cookiecutter.json
project_slug = "{{ cookiecutter.project_slug }}"
# read include_data as a boolean (accepting various truthy values)
include_data_raw = "{{ cookiecutter.include_data }}".strip().lower()
include_data = include_data_raw in ("yes", "y", "true", "1")
project_type = "{{ cookiecutter.project_type }}".lower()
nextflow_as_a_job_raw = "{{ cookiecutter.nextflow_as_a_job }}".strip().lower()
nextflow_as_a_job = nextflow_as_a_job_raw in ("yes", "y", "true", "1")

# get current working directory
cwd = os.path.abspath(os.getcwd())

# if the cwd contains already the project (e.g. cwd == project root) use it,
# otherwise fallback to the hook file location + project_slug
possible_proj = cwd if os.path.basename(cwd) == project_slug or os.path.isdir(os.path.join(cwd, "conf")) else os.path.join(os.path.abspath(os.path.dirname(__file__)), project_slug)
project_dir = os.path.abspath(possible_proj)

# define data directory
data_dir = os.path.join(project_dir, "data")

# define scripts directory
scripts_dir = os.path.join(project_dir, "scripts")

# define params file path
params_path = os.path.join(project_dir, "conf", "params.json")

print(f"Post generation script started in {project_dir}")
print(f"Project type selected: {project_type}")
print(f"Include data folder: {include_data}")
print(f"Params file path: {params_path}")
print(f"Nextflow as a job: {nextflow_as_a_job}")
print(f"Scripts directory path: {scripts_dir}")

# If include_data is false, remove the data directory
if not include_data:
    if os.path.isdir(data_dir):
        shutil.rmtree(data_dir)
        print("Folder 'data/' removed as requested.")

if not nextflow_as_a_job:
    # If not setting up Nextflow as a job, remove the launch script
    os.remove(os.path.join(scripts_dir, "launch.sh"))

# some template configurations for different project types
json_params = {
    "wf-basecalling": {
        "basecaller_cfg": "dna_r10.4.1_e8.2_400bps_sup@v5.2.0",
        "dorado_ext": "pod5",
        "input": "data/pod5",
        "duplex": True,
        "remora_cfg": [
            "dna_r10.4.1_e8.2_400bps_sup@v5.2.0_4mC_5mC@v1",
            "dna_r10.4.1_e8.2_400bps_sup@v5.2.0_6mA@v1"
        ],
        "out_dir": "output"
    },

    "nf-core/methylseq": {
        "input": "<your input here>",
        "fasta": "<genome fasta file>",
        "aligner": "bismark",
        "rrbs": True,
        "outdir": "<your results folder>",
        "save_reference": False,
        "save_align_intermeds": False,
        "save_trimmed": False
    },

    "nf-core/methylong": {
        "input": "<your input here>",
        "pileup_method": "modkit",
        "ont_aligner": "minimap2",
        "bedgraph": True
    },

    "unknown_params": {
        "input": "<your input here>",
        "outdir": "<your results folder>"
    }
}


with open(params_path, "w") as f:
    json.dump(json_params.get(project_type, json_params["unknown_params"]), f, indent=4)
    f.write('\n')

print(f"Project type set to '{project_type}'. Configuration file 'conf/params.json' updated accordingly.")
print("Please edit it further as needed.")

# customize relying on project type
if project_type == "nf-core/methylong":
    shutil.copy(
        os.path.join("{{ cookiecutter._repo_dir }}", "templates", "bedMethyl2cov.py"),
        os.path.join(scripts_dir, "bedMethyl2cov.py")
    )
    print("Custom script 'bedMethyl2cov.py' copied to scripts/ folder for nf-core/methylong project.")
