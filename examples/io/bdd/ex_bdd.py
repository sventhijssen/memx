import os
from pathlib import Path

from memx.cli.Program import Program

file_name = "ham3"

current_directory = Path(os.getcwd())

pla_file_name = "{}.pla".format(file_name)
pla_file_path = current_directory.joinpath(pla_file_name)

spec_file_name = "spec.v".format(file_name)
spec_file_path = current_directory.joinpath(spec_file_name)

bdd_file_name = "{}.bdd".format(file_name)
bdd_file_path = current_directory.joinpath(bdd_file_name)

Program.execute("read {} | sbdd | write {}".format(pla_file_path, bdd_file_path))
Program.execute("read {} | enum {}".format(bdd_file_path, spec_file_path))
