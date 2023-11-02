import os
from pathlib import Path

from cli.Program import Program

file_name = "ham3"

current_directory = Path(os.getcwd())

pla_file_name = "{}.pla".format(file_name)
pla_file_path = current_directory.joinpath(pla_file_name)

spec_file_name = "spec.v".format(file_name)
spec_file_path = current_directory.joinpath(spec_file_name)

topo_sbdd_file_name = "{}_sbdd.topo".format(file_name)
topo_sbdd_file_path = current_directory.joinpath(topo_sbdd_file_name)

topo_robdd_file_name = "{}_robdd.topo".format(file_name)
topo_robdd_file_path = current_directory.joinpath(topo_robdd_file_name)

Program.execute("read {} | sbdd | compact | write {}".format(pla_file_path, topo_sbdd_file_path))
Program.execute("read {} | robdd | compact | write {}".format(pla_file_path, topo_robdd_file_path))

Program.execute("read {} | enum {}".format(topo_sbdd_file_path, spec_file_path))
Program.execute("read {} | enum {}".format(topo_robdd_file_path, spec_file_path))
