import os
import json
import shutil

# get the values from cookiecutter.json
project_slug = "{{ cookiecutter.project_slug }}"
include_data = "{{ cookiecutter.include_data }}".lower()
project_type = "{{ cookiecutter.project_type }}".lower()

# this is the base directory where the script is located
base_dir = os.path.abspath(os.path.dirname(__file__))
project_dir = os.path.join(base_dir, project_slug)

# test for data directory
data_dir = os.path.join(project_dir, "data")

# test for params file
params_path = os.path.join(project_dir, "conf", "params.json")

print(f"Post generation script started in {project_dir}")
print(f"Project type selected: {project_type}")
print(f"Include data folder: {include_data}")
print(f"Params file path: {params_path}")

# If include_data is "no" remove the data directory
if include_data == "no":
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
