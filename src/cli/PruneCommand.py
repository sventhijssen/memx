from utils import config
from cli.Command import Command
from core.decision_diagrams.DDCollection import DDCollection


class PruneCommand(Command):

    def __init__(self):
        """
        Command to apply the prune operation to a collection of decision diagrams.

        Command usage: prune

        """

        super().__init__()

    def execute(self) -> bool:
        context = config.context_manager.get_context()

        assert isinstance(context, DDCollection)

        new_dds = set()
        for dd in context.boolean_functions:
            new_dd = dd.prune()
            new_dd.get_log()
            new_dds.add(new_dd)
        context.boolean_functions = new_dds

        return False
