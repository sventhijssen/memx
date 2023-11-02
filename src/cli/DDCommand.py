from typing import List

from utils import config
from utils.BDDDOTParser import BDDDOTParser
from cli.Command import Command
from core.decision_diagrams.BDDCollection import BDDCollection


class DDCommand(Command):

    def __init__(self, bdd_type: str, args: List[str]):
        """
        Command to invoke the CHECK framework for verification of a crossbar design for flow-based computing
        and a given specification.
        :param args: The BDD type. Either "bdd", "robdd", or "sbdd".
        :param args: A list of required and optional arguments.

        Command usage: bdd|robdd|sbdd [-t VALUE]

        Optional arguments:

        -t VALUE    A timeout  in seconds for the construction of the BDD. By default, set to 3600.

        """

        super().__init__()

        self.dd_type = bdd_type

        if "-t" in args:
            idx = args.index("-t")
            config.time_limit_bdd = int(args[idx + 1])
        else:
            config.time_limit_bdd = 24 * 60 * 60  # 24 hours

        self.args = args

        self.log = {
            "cmd": self.__class__.__name__,
            "args": {
                "dd_type": self.dd_type,
                "time_limit": config.time_limit_bdd,
            },
            "boolean_functions": []
        }

    def execute(self) -> bool:
        boolean_function_collection = config.context_manager.get_context()

        if self.dd_type == "bdd":
            dd_collection = BDDCollection()
        # Reduced Ordered Binary Decision Diagram
        elif self.dd_type == "robdd":
            dd_collection = BDDCollection()
        # Shared Binary Decision Diagram
        elif self.dd_type == "sbdd":
            dd_collection = BDDCollection()
        else:
            raise Exception("Unsupported BDD type.")

        for boolean_function in boolean_function_collection.boolean_functions:
            # Binary Decision Diagram default
            if self.dd_type == "bdd":
                parser = BDDDOTParser(boolean_function)
            # Reduced Ordered Binary Decision Diagram
            elif self.dd_type == "robdd":
                parser = BDDDOTParser(boolean_function, False)
            # Shared Binary Decision Diagram
            elif self.dd_type == "sbdd":
                parser = BDDDOTParser(boolean_function)
            else:
                raise Exception("Unsupported BDD type.")

            sub_dd_collection = parser.parse()
            for sub_dd in sub_dd_collection.boolean_functions:
                dd_collection.add(sub_dd)
                self.log["boolean_functions"].append(sub_dd.get_log())

        config.context_manager.add_context("", dd_collection)

        return False
