import math
from pathlib import Path
from typing import List

from utils import config
from utils.BenchmarkReader import BenchmarkReader
from cli.Command import Command
from core.benchmarks.Benchmark import VerilogBenchmark
from verf.DynamicGraphTree import DynamicGraphTree
from verf.StaticGraphTree import StaticGraphTree


class CHECKCommand(Command):

    def __init__(self, args: List[str]):
        """
        Command to invoke the CHECK framework for verification of a crossbar design for flow-based computing
        and a given specification.
        :param args: A list of required and optional arguments.

        Command usage: check SPEC_FILE_PATH [-s VALUE] [-static] [-r]

        The first argument must be the file path of a specification in Verilog file format.

        Optional arguments:

        -s VALUE    The sampling size to be performed in parallel.

        -static     Turns off dynamic path extraction.

        -r          Turns on recording of the formulae extracted from the crossbar design.

        """

        super().__init__()

        if len(args) < 1:
            raise Exception("Specification not provided.")

        self.specification_file_path = Path(args[0])

        if "-s" in args:
            idx = args.index("-s")

            try:
                self.sampling_size = int(args[idx + 1])
            except Exception as e:
                self.sampling_size = -1
        else:
            self.sampling_size = 0

        if "-static" in args:
            self.dynamic = False
        else:
            self.dynamic = True

        if "-r" in args:
            config.record_formulae = True
        else:
            config.record_formulae = False

    def execute(self) -> bool:
        print("CHECK started")
        context = config.context_manager.get_context()
        crossbar = list(context.boolean_functions)[0]

        benchmark_reader = BenchmarkReader(self.specification_file_path)
        boolean_function_collection_specification = benchmark_reader.read()

        # If no sampling size was provided, but we do want sampling, then we sample over all input vectors.
        if self.sampling_size == -1:
            self.sampling_size = int(math.pow(2, len(boolean_function_collection_specification.input_variables)))

        specification = list(boolean_function_collection_specification.boolean_functions)[0]
        assert isinstance(specification, VerilogBenchmark)

        if self.dynamic:
            check = DynamicGraphTree(crossbar, specification)
        else:
            check = StaticGraphTree(crossbar, specification)

        check.is_equivalent(sampling_size=self.sampling_size)

        print("CHECK stopped")
        print()
        return False
