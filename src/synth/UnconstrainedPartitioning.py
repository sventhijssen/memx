from __future__ import annotations

import time
from typing import List, Dict, Any

from networkx import MultiDiGraph, DiGraph
from networkx.algorithms.bipartite import sets

from core.hardware.Crossbar import SelectorCrossbar
from core.hardware.Topology import Topology
from core.expressions.BooleanExpression import LITERAL
from synth.PartitioningMethod import PartitioningMethod


class UnconstrainedPartitioning(PartitioningMethod):
    """
    An unconstrained partitioning method.
    """

    def __init__(self, bipartite_graph: DiGraph):
        """

        :param bipartite_graph:
        """
        super().__init__(bipartite_graph)
        self.U, self.V = sets(self.graph)

    def get_log(self) -> List[Dict[str, Any]] | Dict[str, Any]:
        return {
            "type": self.__class__.__name__,
            "bipartite_graph": {
                "U": len(self.U),
                "V": len(self.V),
                "E": len(self.graph.edges)
            },
            "topology":
                self.topology.get_log(),
            "time": self.end_time - self.start_time
        }

    def partition(self) -> Topology:
        self.start_time = time.time()

        rows = len(self.U)
        columns = len(self.V)
        crossbar = SelectorCrossbar(rows, columns)

        # We assign the nodes (nodes in the set U) and edges (nodes in the set V) of the BDD to the crossbar
        crossbar.selectorlines = list(self.V)
        crossbar.wordlines = list(self.U)

        # We set the output(s) of the crossbar
        node_output_variables = list(map(lambda u: (u, self.graph.nodes[u]["output_variables"]), filter(lambda u: self.graph.nodes[u]["root"] == True, self.U)))
        for (node, output_variables) in node_output_variables:
            row = crossbar.wordlines.index(node)
            for output_variable in output_variables:
                crossbar.set_output_nanowire(output_variable, row)

        # We set the input(s) of the crossbar
        node_input_variables = list(map(lambda u: (u, self.graph.nodes[u]["variable"]), filter(lambda u: self.graph.nodes[u]["terminal"] == True, self.U)))
        for (node, input_variable) in node_input_variables:
            row = crossbar.wordlines.index(node)
            crossbar.set_input_nanowire(input_variable, row)

        # For each edge e=(u,v), we will program the respective memristor ON.
        for (u, v) in self.graph.edges:
            if u in self.U:
                r = crossbar.wordlines.index(u)
                c = crossbar.selectorlines.index(v)
            else:
                r = crossbar.wordlines.index(v)
                c = crossbar.selectorlines.index(u)
            crossbar.set_memristor(r, c, LITERAL("True", True))

        # We replace the nodes assigned to the selectorlines with their respective literals.
        for i in range(columns):
            crossbar.selectorlines[i] = self.graph.nodes[crossbar.selectorlines[i]]["literal"]

        self.end_time = time.time()

        topology_graph = MultiDiGraph()
        topology_graph.add_node(crossbar)

        self.topology = Topology(topology_graph)
        return self.topology

