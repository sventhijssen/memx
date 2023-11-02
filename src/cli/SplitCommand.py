from utils import config
from cli.Command import Command
from core.BooleanFunctionCollection import BooleanFunctionCollection
from core.benchmarks.Benchmark import BLIFBenchmark


class SplitCommand(Command):

    def __init__(self):
        """
        Command to split the Boolean function collection to file. Currently only supports BLIF benchmarks.

        Command usage: split

        """

        super().__init__()

    def execute(self) -> bool:
        multi_output_boolean_function_collection = config.context_manager.get_context()

        new_boolean_functions = set()
        for boolean_function in multi_output_boolean_function_collection.boolean_functions:
            assert isinstance(boolean_function, BLIFBenchmark)

            blif_benchmarks = boolean_function.split()

            new_boolean_functions.update(blif_benchmarks)

        config.context_manager.add_context("split", BooleanFunctionCollection(new_boolean_functions))

        return False
