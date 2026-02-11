import os
import json
import shutil

# get the values from cookiecutter.json
project_slug = "{{ cookiecutter.project_slug }}"
# read include_data as a boolean (accepting various truthy values)
include_data_raw = "{{ cookiecutter.include_data }}".strip().lower()
include_data = include_data_raw in ("yes", "y", "true", "1")
project_type = "{{ cookiecutter.project_type }}".lower()

# get current working directory
cwd = os.path.abspath(os.getcwd())

# if the cwd contains already the project (e.g. cwd == project root) use it,
# otherwise fallback to the hook file location + project_slug
possible_proj = cwd if os.path.basename(cwd) == project_slug or os.path.isdir(os.path.join(cwd, "conf")) else os.path.join(os.path.abspath(os.path.dirname(__file__)), project_slug)
project_dir = os.path.abspath(possible_proj)

# define data directory
data_dir = os.path.join(project_dir, "data")

# test for params file
# define params file path
params_path = os.path.join(project_dir, "conf", "params.json")

print(f"Post generation script started in {project_dir}")
print(f"Project type selected: {project_type}")
print(f"Include data folder: {include_data}")
print(f"Params file path: {params_path}")

# If include_data is false, remove the data directory
if not include_data:
    if os.path.isdir(data_dir):
        shutil.rmtree(data_dir)
        print("Folder 'data/' removed as requested.")
    else:
        print("No 'data/' folder to remove.")

# some template configurations for different project types
wf_basecalling_params = {
    "basecaller_cfg": "dna_r10.4.1_e8.2_400bps_sup@v5.2.0",
    "dorado_ext": "pod5",
    "input": "data/pod5",
    "duplex": True,
    "remora_cfg": [
        "dna_r10.4.1_e8.2_400bps_sup@v5.2.0_4mC_5mC@v1",
        "dna_r10.4.1_e8.2_400bps_sup@v5.2.0_6mA@v1"
    ],
    "out_dir": "output"
}

unknown_params = {
    "input": "<your input here>"
}


if project_type == "wf-basecalling":
    with open(params_path, "w") as f:
        json.dump(wf_basecalling_params, f, indent=4)
        f.write('\n')
else:
    with open(params_path, "w") as f:
        json.dump(unknown_params, f, indent=4)
        f.write('\n')

print(f"Project type set to '{project_type}'. Configuration file 'conf/params.json' updated accordingly.")
print("Please edit it further as needed.")
