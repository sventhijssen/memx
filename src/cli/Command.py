from abc import ABC, abstractmethod


class Command(ABC):
    """
    Base class for commands.

    A command can be initialized using command line arguments and executes.

    """

    def __init__(self):
        """
        Initializes the command. Command line arguments can be passed and attributes can be set for execution.
        """
        pass

    @abstractmethod
    def execute(self) -> bool:
        """
        Executes the command using the attributes of this command.
        Returns true if and only if the command halt the execution of the program.
        :return: True if and only if the program halts.
        """
        pass
