import pexpect

from utils import config
from utils.KLUTParser import KLUTParser
from cli.Command import Command
from core.BooleanFunctionCollection import BooleanFunctionCollection


class KLUTCommand(Command):

    def __init__(self, args):
        """
        Command to invoke the ISO framework for path-based computing.
        :param args: A list of required and optional arguments.

        Command usage: klut [-D VALUE]

        Optional arguments:

        -D VALUE    The maximum dimension for the crossbar design.
        """

        super().__init__()

        if "-K" in args:
            idx = args.index("-K")
            self.K = int(args[idx + 1])
        else:
            self.K = None

        if "-G" in args:
            idx = args.index("-G")
            self.G = int(args[idx + 1])
        else:
            self.G = None

    def execute(self) -> bool:
        boolean_function_collection = config.context_manager.get_context()

        # TODO: Fix for multiple functions
        collection = None
        for boolean_function in boolean_function_collection.boolean_functions:
            parser = KLUTParser(boolean_function, self.K, self.G)
            bdd_topology = parser.parse()
            collection = bdd_topology

        config.context_manager.add_context("", collection)

        return False
