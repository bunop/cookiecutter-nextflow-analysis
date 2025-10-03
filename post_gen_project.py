import os
import shutil

# get the value of include_data from cookiecutter context
include_data = "{{ cookiecutter.include_data }}".lower()

# this is the base directory where the script is located
project_dir = os.path.abspath(os.path.dirname(__file__))

data_dir = os.path.join(project_dir, "data")

# If include_data is "no" remove the data directory
if include_data == "no":
    if os.path.isdir(data_dir):
        shutil.rmtree(data_dir)
        print("Folder 'data/' removed as requested.")
    else:
        print("No 'data/' folder to remove.")
