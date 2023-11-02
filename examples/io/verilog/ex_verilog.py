import os
from pathlib import Path

from cli.Program import Program

file_name = "ham3"

current_directory = Path(os.getcwd())

verilog_file_name = "{}.v".format(file_name)
verilog_file_path = current_directory.joinpath(verilog_file_name)

spec_file_name = "spec.v".format(file_name)
spec_file_path = current_directory.joinpath(spec_file_name)

Program.execute("read {} | enum {}".format(verilog_file_path, spec_file_path))
