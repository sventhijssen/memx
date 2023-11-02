import time
from typing import Type, Dict, Any

from networkx import DiGraph

from utils import config
from core.expressions.BooleanExpression import LITERAL
from core.hardware.Topology import Topology
from exceptions.InfeasibleSolutionException import InfeasibleSolutionException
from synth.PartitioningMethod import PartitioningMethod
from synth.SynthesisMethod import SynthesisMethod
from core.decision_diagrams.BDD import BDD


class PATH(SynthesisMethod):
    """
    Implementation for the synthesis method PATH.
    """

    def __init__(self, bdd: BDD, partitioning_method_type: Type[PartitioningMethod]):
        """
        Given a BDD, a partitioning method and optional hardware constraints,
        PATH maps the data structure to a topology of crossbars.
        The hardware constraints include constraints on the dimensions of crossbars in a staircase structure
        (provided as a list of integers D_0, D_1, ..., D_n where D_0 is the dimension of the first crossbar
        and D_n is the dimension of the last crossbar), and constraints on the inter-crossbar connections.
        :param bdd: The given BDD.
        :param partitioning_method_type:
        """
        super().__init__(bdd)
        self.partitioning_method_type = partitioning_method_type
        self.partitioning_method = partitioning_method_type(self._bdd_to_bipartite_graph())

    def _bdd_to_bipartite_graph(self) -> DiGraph:
        """
        A bipartite bipartite_graph B = (U, V, E) is constructed from the BDD bipartite_graph G = (W, F)
        where one set of nodes U = W, one set of nodes V = F,
        and the set of edges E = {e0, e1 | e0 = (u,e), e1 = (v,e), ∀e=(u, v) ∈ F}.
        Note that the edges are reversed from the edges in the BDD.

        If edge optimization is applied, we merge incoming edges e_i of node u which have the same literal l.
        Assume an edge e is represented by (u, v, l) where u is the current node, v is a parent node,
        and l is the literal of the edge. Say we have edges e0 = (u, v0, l) and e1 = (u, v1, l), v0 != v1, e0, e1 ∈ F
        then in the bipartite bipartite_graph B, we have U ∪ {u, v0, v1}, V ∪ {e0}, E ∪ {(u, e0), (v0, e1), (v1, e0))}.

        We follow the suggested approach from
        https://networkx.org/documentation/stable/reference/algorithms/bipartite.html
        to construct a bipartite bipartite_graph in NetworkX.
        :return:
        """
        dag = self.dd.dag

        B = DiGraph()
        if len(dag.nodes) == 0:
            B.add_node("1", bipartite=0, **{"terminal": True, "root": False, "variable": 1, "output_variables": set()})
            B.add_node("2", bipartite=0, **{"terminal": False, "root": True, "variable": 2, "output_variables": {self.dd.get_name()}})
            B.add_node("(2, 1)", bipartite=1, literal=LITERAL("False", False))  # Dummy edge
            B.add_edge("1", "(2, 1)")
            B.add_edge("(2, 1)", "2")
            return B

        for u, node_data in dag.nodes(data=True):
            if "output_variables" not in node_data:
                node_data["output_variables"] = set()
            B.add_node(u, bipartite=0, **node_data)

        for u in dag.nodes:
            for edge in dag.in_edges(u):
                (v, _) = edge
                edge_data = dag.get_edge_data(v, u)
                B.add_node(edge, bipartite=1, literal=edge_data.get("literal"))
                B.add_edge(u, edge)
                B.add_edge(edge, v)
        return B

    def map(self) -> Topology:
        print("PATH started")

        self.start_time = time.time()
        try:
            topology = self.partitioning_method.partition()
        except InfeasibleSolutionException:
            self.end_time = time.time()
            config.log.add_json(self.get_log())
            raise InfeasibleSolutionException()
        self.end_time = time.time()

        config.log.add_json(self.get_log())
        print("PATH stopped")
        return topology

    def get_log(self) -> Dict[str, Any]:
        return {
            "type": self.__class__.__name__,
            "partitioning_method": self.partitioning_method.get_log(),
            "time": self.end_time - self.start_time,
        }
