from abc import ABC

from networkx import DiGraph, is_directed_acyclic_graph, is_weakly_connected

from core.BooleanFunction import BooleanFunction
from core.DrawInterface import DrawInterface
from core.IOInterface import IOInterface


class DD(BooleanFunction, IOInterface, DrawInterface, ABC):

    def __init__(self, graph: DiGraph, name: str = None):
        super().__init__(name)
        self.root_nodes = set()

        # The given graph must be a DAG.
        if not is_directed_acyclic_graph(graph):
            raise Exception("Given graph is not a DAG.")

        # The given graph must be weakly connected.
        if len(graph.nodes) > 0 and not is_weakly_connected(graph):
            raise Exception("Given graph is not weakly connected.")

        self.dag = graph
