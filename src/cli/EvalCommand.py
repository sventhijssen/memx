from pathlib import Path
from typing import List

from utils import config
from utils.InstanceFileReader import InstanceFileReader
from cli.Command import Command


class EvalCommand(Command):

    def __init__(self, args: List[str]):
        """
        Command to evaluate the network for the given input instance.
        :param args: A list of required and optional arguments.

        Command usage: eval INSTANCE_FILE_PATH

        The first argument must be the file path of an input instance in INPUT file format.

        """

        super().__init__()
        if len(args) < 1:
            raise Exception("Unknown instance file.")

        self.instance_file = args[0]

    def execute(self) -> bool:
        context = config.context_manager.get_context()

        instance_file_reader = InstanceFileReader(self.instance_file)
        instance = instance_file_reader.parse()

        evaluation = context.eval(instance)

        print(evaluation)

        return False
