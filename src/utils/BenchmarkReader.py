from pathlib import Path

from utils import config
from core.BooleanFunctionCollection import BooleanFunctionCollection
from core.benchmarks.Benchmark import BLIFBenchmark, PLABenchmark, VerilogBenchmark
from core.hardware.Crossbar import Crossbar
from core.decision_diagrams.BDDCollection import BDDCollection
from core.hardware.Topology import Topology


class BenchmarkReader:

    def __init__(self, file_path: Path):
        """
        Reads a benchmark from file with the given file path.
        :param file_path: The given file path of the file to be read.
        """
        self.file_path = file_path

    def read(self) -> BooleanFunctionCollection:
        """
        Reads the benchmark from file.
        :return: A Boolean function collection.
        """
        benchmark_name = self.file_path.stem
        file_extension = self.file_path.suffix

        print("Started reading benchmark \"{}\"".format(benchmark_name))

        if file_extension == ".pla":
            benchmark = PLABenchmark.read(config.root.joinpath(self.file_path))
            boolean_function_collection = BooleanFunctionCollection({benchmark})
        elif file_extension == ".blif":
            benchmark = BLIFBenchmark.read(config.root.joinpath(self.file_path))
            boolean_function_collection = BooleanFunctionCollection({benchmark})
        elif file_extension == ".v":
            benchmark = VerilogBenchmark.read(config.root.joinpath(self.file_path))
            boolean_function_collection = BooleanFunctionCollection({benchmark})
        elif file_extension == ".bdd":
            boolean_function_collection = BDDCollection.read(config.root.joinpath(self.file_path))
        elif file_extension == ".xbar":
            crossbar = Crossbar.read(self.file_path)
            boolean_function_collection = BooleanFunctionCollection({crossbar})
        elif file_extension == ".topo":
            topology = Topology.read(self.file_path)
            boolean_function_collection = BooleanFunctionCollection({topology})
        else:
            raise Exception("Unsupported file type.")

        print("Stopped reading benchmark")
        print()

        return boolean_function_collection
