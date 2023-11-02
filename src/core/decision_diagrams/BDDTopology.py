from typing import Dict, Set

from networkx import DiGraph

from core.BooleanFunction import BooleanFunction
from core.BooleanFunctionCollection import BooleanFunctionCollection
from core.DrawInterface import DrawInterface
from core.decision_diagrams.BDD import BDD


class BDDTopology(BooleanFunctionCollection, DrawInterface):

    def __init__(self, topology: DiGraph, bdds: Dict[str, BDD]):
        super().__init__()
        self.topology = topology
        self.bdds = bdds

    def get_input_variables(self) -> Set[str]:
        input_variables = set()
        for node in self.topology:
            assert isinstance(node, BDD)
            input_variables.update(node.get_input_variables())
        return input_variables

    def get_output_variables(self) -> Set[str]:
        output_variables = set()
        for node in self.topology:
            assert isinstance(node, BDD)
            output_variables.update(node.get_output_variables())
        return output_variables

    def get_auxiliary_variables(self) -> Set[str]:
        return set()

    def get_boolean_functions(self) -> Set[BooleanFunction]:
        bdds = set()
        for bdd in self.bdds.values():
            bdds.add(bdd)
        return bdds

    def eval(self, instance: Dict[str, bool]) -> Dict[str, bool]:
        raise NotImplementedError()

    def to_dot(self) -> str:
        raise NotImplementedError()
