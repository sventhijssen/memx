from pathlib import Path
from typing import List

from utils import config
from utils.BenchmarkReader import BenchmarkReader
from cli.Command import Command
from core.benchmarks.Benchmark import VerilogBenchmark
from verf.XSAT import XSAT


class XSATCommand(Command):

    def __init__(self, args: List[str]):
        """
        Command to invoke the XSAT framework for verification of a crossbar design for flow-based computing
        and a given specification.
        :param args: A list of required and optional arguments.

        Command usage: xsat SPEC_FILE_PATH [-T VALUE] [-D VALUE]

        The first argument must be the file path of a specification in Verilog file format.

        Optional arguments:

        -T VALUE    The node threshold to stop expanding a branch in the divide-and-conquer technique.

        -D VALUE    The maximum depth for the divide-and-conquer technique.
        """

        super().__init__()

        if len(args) < 1:
            raise Exception("Specification not provided.")

        self.specification_file_path = Path(args[0])

        if "-T" in args:
            self.node_threshold = int(args[args.index("-T") + 1])
        else:
            self.node_threshold = None

        if "-D" in args:
            self.depth_threshold = int(args[args.index("-D") + 1])
        else:
            self.depth_threshold = None

    def execute(self) -> bool:
        boolean_function_collection = config.context_manager.get_context()

        benchmark_reader = BenchmarkReader(self.specification_file_path)
        specification = benchmark_reader.read()

        assert isinstance(specification, VerilogBenchmark)

        # TODO: Fix
        for boolean_function in boolean_function_collection.boolean_functions:
            xsat = XSAT(boolean_function, specification, self.node_threshold, self.depth_threshold)
            xsat.is_equivalent()
        return False
