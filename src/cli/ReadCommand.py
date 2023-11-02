from pathlib import Path
from typing import List

from utils import config
from utils.BenchmarkReader import BenchmarkReader
from cli.Command import Command


class ReadCommand(Command):

    def __init__(self, args: List[str]):
        """
        Command to read the Boolean function collection from file.
        :param args: A list of required and optional arguments.

        Command usage: read FILE_PATH

        The first argument must be the file path.

        """

        super().__init__()

        if len(args) < 1:
            raise Exception("Missing file path.")

        self.file_path = Path(args[0])

    def execute(self) -> bool:
        benchmark_reader = BenchmarkReader(self.file_path)
        boolean_function_collection = benchmark_reader.read()
        config.context_manager.add_context("", boolean_function_collection)

        return False
