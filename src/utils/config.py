import pathlib
import platform
import sys

from cli.ContextManager import ContextManager
from utils.Log import Log

context_manager = ContextManager()
log = Log()

# Settings for DD
time_limit_bdd = 3600

# Settings for COMPACT
# Apply VH-labeling (2D crossbars) or K-labeling (3D crossbars)
vh_labeling = False
# Apply input and output constraints
io_constraints = True
# Input layer
input_layer = None
# Output layer
output_layer = None
# Apply a time limit
time_limit = None
# Keep auxiliary files from CPLEX
keep_files = False
# By default, the objective of COMPACT is to optimize the semiperimeter (only for K-labeling)
# Other option = "cs" for "constraint solving" (no minimization)
objective = "semi"
gamma = 1
max_rows = sys.maxsize
max_columns = sys.maxsize

record_formulae = False

root = pathlib.Path(__file__).parent.parent.parent.absolute()
abc_path = root.joinpath('abc')

if platform.system() == 'Windows':
    bash_cmd = ['bash', '-c']
    cplex_path = '/opt/ibm/ILOG/CPLEX_Studio201/cplex/bin/x64_win64/cplex.exe'
elif platform.system() == 'Linux':
    bash_cmd = ['/bin/bash', '-c']
    cplex_path = '/opt/ibm/ILOG/CPLEX_Studio201/cplex/bin/x86-64_linux/cplex'
elif platform.system() == 'Darwin':
    bash_cmd = ['/bin/bash', '-c']
    cplex_path = '/Applications/CPLEX_Studio_Community2211/cplex/bin/x86-64_osx/cplex'
else:
    raise Exception("Unsupported OS: {}".format(platform.system()))

abc_cmd = bash_cmd.copy()
abc_cmd.extend(['"./abc"'])
abc_cmd = ' '.join(abc_cmd)

equivalence_checker_timeout = 3600
