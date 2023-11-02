from pathlib import Path
from typing import List

from utils import config
from utils.BenchmarkReader import BenchmarkReader
from core.benchmarks.Benchmark import VerilogBenchmark
from verf.Enumeration import Enumeration
from cli.Command import Command


class EnumerationCommand(Command):

    def __init__(self, args: List[str]):
        """
        Command to apply brute-force enumeration for verification on a network and a given specification.
        :param args: A list of required and optional arguments.

        Command usage: enum SPEC_FILE_PATH [-s VALUE]

        The first argument must be the file path of a specification.

        Optional arguments:

        -s VALUE    The sampling size to be performed. If provided, then the whole truth table will not be enumerated.

        """

        super(EnumerationCommand).__init__()
        if len(args) < 1:
            raise Exception("Specification not provided.")

        self.specification_file_path = Path(args[0])

        if "-s" in args:
            idx = args.index("-s")
            self.sampling_size = int(args[idx + 1])
        else:
            self.sampling_size = 0

    def execute(self) -> bool:
        boolean_function_collection = config.context_manager.get_context()

        benchmark_reader = BenchmarkReader(self.specification_file_path)
        specification = benchmark_reader.read()

        enumeration = Enumeration(boolean_function_collection, specification)
        enumeration.is_equivalent(self.sampling_size)

        return False
