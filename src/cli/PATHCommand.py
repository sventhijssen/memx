from utils import config
from core.decision_diagrams.BDD import BDD
from core.BooleanFunctionCollection import BooleanFunctionCollection
from synth.PATH import PATH
from cli.Command import Command
from synth.UnconstrainedPartitioning import UnconstrainedPartitioning


class PATHCommand(Command):

    def __init__(self):
        """
        Command to invoke the PATH framework for path-based computing. The network must be in BDD format.

        Command usage: path

        """
        super(PATHCommand).__init__()

        self.partitioning_scheme = UnconstrainedPartitioning

    def execute(self) -> bool:
        collection = config.context_manager.get_context()

        new_boolean_functions = set()
        for boolean_function in collection.boolean_functions:
            assert isinstance(boolean_function, BDD)

            path = PATH(boolean_function, self.partitioning_scheme)
            topology = path.map()

            new_boolean_functions.add(topology)

        config.context_manager.add_context("", BooleanFunctionCollection(new_boolean_functions))
        return False
