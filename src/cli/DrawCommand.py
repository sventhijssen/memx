from pathlib import Path
from typing import List

from utils import config
from cli.Command import Command
from core.DrawInterface import DrawInterface


class DrawCommand(Command):

    def __init__(self, args: List[str]):
        """
        Command to draw the current network in DOT file format.
        :param args: A list of required and optional arguments.

        Command usage: draw FILE_NAME

        The first argument must be the file name. A network may be a collection of Boolean functions.
        A DOT file will be created for each subnetwork.

        """

        super().__init__()

        if len(args) < 1:
            raise Exception("Missing file path.")

        self.file_path = Path(args[0])

    def execute(self) -> bool:
        context = config.context_manager.get_context()

        i = 0
        for boolean_function in context.get_boolean_functions():
            assert isinstance(boolean_function, DrawInterface)

            file_path = self.file_path.stem + "_" + str(i) + self.file_path.suffix
            content = boolean_function.to_dot()
            for sub_content in content:
                with open(file_path, 'w') as f:
                    f.write(sub_content)
            i += 1
        return False
