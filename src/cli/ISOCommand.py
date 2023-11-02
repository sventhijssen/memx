from typing import List

from utils import config
from synth.ISO import ISO
from core.decision_diagrams.BDDCollection import BDDCollection
from core.decision_diagrams.BDDTopology import BDDTopology
from cli.Command import Command


class ISOCommand(Command):

    def __init__(self, args: List[str]):
        """
        Command to invoke the ISO framework for path-based computing.
        :param args: A list of required and optional arguments.

        Command usage: iso [-D VALUE]

        Optional arguments:

        -D VALUE    The maximum dimension for the crossbar design.

        """

        super().__init__()

        if "-D" not in args:
            self.dimension = None
        else:
            idx = args.index("-D")
            self.dimension = int(args[idx + 1])

    def execute(self) -> bool:
        context = config.context_manager.get_context()

        bdd_collection = BDDCollection()

        assert isinstance(context, BDDTopology)
        bdd_isomorphism = ISO(context, self.dimension)
        bdd_isomorphism.find()

        config.context_manager.add_context("bdd_collection", bdd_collection)

        return False
