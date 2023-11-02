from cli.ISOCommand import ISOCommand
from cli.DDCommand import DDCommand
from cli.COMPACTCommand import COMPACTCommand
from cli.ChakrabortyCommand import ChakrabortyCommand
from cli.CHECKCommand import CHECKCommand
from cli.DrawCommand import DrawCommand
from cli.EnumerationCommand import EnumerationCommand
from cli.EvalCommand import EvalCommand
from cli.ExitCommand import ExitCommand
from cli.KLUTCommand import KLUTCommand
from cli.LogCommand import LogCommand
from cli.PATHCommand import PATHCommand
from cli.PruneCommand import PruneCommand
from cli.ReadCommand import ReadCommand
from cli.SplitCommand import SplitCommand
from cli.WriteCommand import WriteCommand
from cli.XSATCommand import XSATCommand


class CommandParser:

    @staticmethod
    def parse(raw_command: str):
        """
        Parses the given command. The command is split into tokens by a whitespace.
        The first token is the command name, upon which the correct command is called with the respective arguments.
        :param raw_command: A command in the format of one string.
        :return: Returns the command based on the first token in the given command string.

        I/O commands:
        - log
        - read
        - write
        - draw

        Synthesis commands:
        - bdd
        - robdd
        - sbdd
        - chakraborty
        - compact
        - path
        - klut
        - iso

        Verification commands:
        - enum
        - check
        - xsat

        Auxiliary commands:
        - eval
        - split
        - prune

        """

        command_list = raw_command.strip().split(" ")
        command_name = command_list[0]
        args = command_list[1:]

        if command_name == "exit":
            return ExitCommand()

        # I/O commands:
        elif command_name == "log":
            return LogCommand(args)
        elif command_name == "read":
            return ReadCommand(args)
        elif command_name == "write":
            return WriteCommand(args)
        elif command_name == "draw":
            return DrawCommand(args)

        # Synthesis commands:
        elif command_name == "bdd":
            return DDCommand("bdd", args)
        elif command_name == "robdd":
            return DDCommand("robdd", args)
        elif command_name == "sbdd":
            return DDCommand("sbdd", args)
        elif command_name == "chakraborty":
            return ChakrabortyCommand()
        elif command_name == "compact":
            return COMPACTCommand(args)
        elif command_name == "path":
            return PATHCommand()
        elif command_name == "klut":
            return KLUTCommand(args)
        elif command_name == "iso":
            return ISOCommand(args)

        # Verification commands:
        elif command_name == "enum":
            return EnumerationCommand(args)
        elif command_name == "check":
            return CHECKCommand(args)
        elif command_name == "xsat":
            return XSATCommand(args)

        # Auxiliary commands:
        elif command_name == "eval":
            return EvalCommand(args)
        elif command_name == "split":
            return SplitCommand()
        elif command_name == "prune":
            return PruneCommand()
        else:
            raise Exception("Unknown command.")
