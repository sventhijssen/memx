from pathlib import Path

from utils import config
from cli.Command import Command
from core.BooleanFunction import BooleanFunction
from core.IOInterface import IOInterface


class WriteCommand(Command):

    def __init__(self, args):
        """
        Command to write the Boolean function collection to file.
        :param args: A list of required and optional arguments.

        Command usage: write [FILE_PATH]

        The first argument is an optional file path. However, be careful!
        When the Boolean function collection contains more than one Boolean function,
        then it will override the same file.

        Optional arguments:

        FILE_PATH  The file path.

        """

        super().__init__()

        if len(args) < 1:
            self.file_path = None
        else:
            self.file_path = Path(args[0])

    def execute(self) -> bool:
        boolean_function_collection = config.context_manager.get_context()

        for boolean_function in boolean_function_collection.boolean_functions:
            assert isinstance(boolean_function, BooleanFunction)
            if self.file_path is None:
                self.file_path = boolean_function.get_file_path()

            assert isinstance(boolean_function, IOInterface)
            boolean_function.write(self.file_path)

        return False
