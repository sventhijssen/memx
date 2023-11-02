from cli.Command import Command


class ExitCommand(Command):

    def __init__(self):
        """
        Command to exit the MemX program.

        Command usage: exit

        """

        super().__init__()

    def execute(self) -> bool:
        return True
