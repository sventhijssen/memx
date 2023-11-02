import os
from pathlib import Path

from cli.Program import Program

file_name = "ham3"

current_directory = Path(os.getcwd())

blif_file_name = "{}.blif".format(file_name)
blif_file_path = current_directory.joinpath(blif_file_name)

spec_file_name = "spec.v".format(file_name)
spec_file_path = current_directory.joinpath(spec_file_name)

Program.execute("read {} | enum {}".format(blif_file_path, spec_file_path))
