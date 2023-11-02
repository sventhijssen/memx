from utils import config
from core.BooleanFunctionCollection import BooleanFunctionCollection
from core.decision_diagrams.BDD import BDD
from core.decision_diagrams.BDDCollection import BDDCollection
from synth.ChakrabortyAutomatedSynthesis import ChakrabortyAutomatedSynthesis
from cli.Command import Command


class ChakrabortyCommand(Command):

    def __init__(self):
        """
        Command to invoke Dr. Chakraborty's automated synthesis method for flow-based computing.

        Command usage: chakraborty

        """

        super().__init__()

    def execute(self) -> bool:
        boolean_function_collection = config.context_manager.get_context()

        assert isinstance(boolean_function_collection, BDDCollection)

        new_boolean_function_collection = BooleanFunctionCollection()
        for bdd in boolean_function_collection.boolean_functions:
            assert isinstance(bdd, BDD)

            chakraborty = ChakrabortyAutomatedSynthesis(bdd)
            topology = chakraborty.map()
            new_boolean_function_collection.add(topology)

        config.context_manager.add_context("", new_boolean_function_collection)
        return False
