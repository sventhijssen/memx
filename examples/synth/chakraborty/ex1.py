import os
from pathlib import Path

from cli.Program import Program

file_name = "ham3"

current_directory = Path(os.getcwd())

log_file_name = "{}.log".format(file_name)
log_file_path = current_directory.joinpath(log_file_name)

pla_file_name = "{}.pla".format(file_name)
pla_file_path = current_directory.joinpath(pla_file_name)

topo_file_name = "{}_sbdd.topo".format(file_name)
topo_file_path = current_directory.joinpath(topo_file_name)

Program.execute("log {} | read {} | sbdd | chakraborty | write {}".format(log_file_path, pla_file_path, topo_file_path))
