import enum
import time
from typing import Any

from networkx import Graph, set_node_attributes
from z3 import And, Bool, Solver, unsat, Not, Or

from utils import config
from utils.Z3Converter import Z3Converter
from core.BooleanFunction import BooleanFunction
from core.benchmarks.Benchmark import VerilogBenchmark
from core.expressions.BooleanExpression import LITERAL
from core.hardware.Crossbar import MemristorCrossbar
from verf.EquivalenceChecker import EquivalenceChecker


class Color(enum.Enum):
    white = 0
    gray = 1
    black = 2


class SimplePathTree(EquivalenceChecker):

    def __init__(self, boolean_function: BooleanFunction, specification: BooleanFunction):
        super().__init__(boolean_function, specification)
        self.start_time = None
        self.stop_time = None
        self.conjunctions = dict()
        for output_variable in self.specification.output_variables():
            self.conjunctions[output_variable] = set()

    @staticmethod
    def _entails(sentence_a: Bool, sentence_b: Bool) -> bool:
        s = Solver()
        s.add(And(sentence_a, Not(sentence_b)))
        return s.check() == unsat

    def _dfs_visit(self, graph: Graph, u: Any) -> bool:
        graph.nodes[u]["color"] = Color.gray

        output = graph.nodes[u]["output"]
        output_variables = graph.nodes[u]["output_variables"]
        visited = graph.nodes[u]["visited"]

        if output:
            for output_variable in output_variables:
                z3_literals = set(map(lambda l: Bool(l.atom) if l.positive else Not(Bool(l.atom)), visited))
                sentence_a = And(z3_literals)
                # print(sentence_a)
                # sentence_b = Z3Converter.verilog_to_z3(self.boolean_function_b.wordlines.get(output_variable).verilog)
                # # print(sentence_b)
                # if not self._entails(sentence_a, sentence_b):
                #     return False
                self.conjunctions[output_variable].add(sentence_a)
                # return True

        for v in graph.neighbors(u):
            if graph.nodes[v]["color"] == Color.white:
                edge_data = graph.get_edge_data(u, v)
                literal = edge_data["literal"]
                # print(literal)
                if literal == LITERAL("True", True):
                    graph.nodes[v]["visited"] = visited.copy()
                    if not self._dfs_visit(graph, v):
                        return False
                elif literal in visited:
                    graph.nodes[v]["visited"] = visited.copy()
                    if not self._dfs_visit(graph, v):
                        return False
                elif literal.negate() in visited:
                    pass
                    # graph.nodes[v]["visited"] = visited.copy()
                else:
                    graph.nodes[v]["visited"] = visited.copy()
                    graph.nodes[v]["visited"].add(literal)
                    if not self._dfs_visit(graph, v):
                        return False
        graph.nodes[u]["color"] = Color.white
        # graph.nodes[u]["visited"] = set()
        return True

    def _halt(self, equivalent: bool = False) -> bool:
        self.stop_time = time.time()
        total_time = self.stop_time - self.start_time
        config.log.add("CHECK time: {}".format(total_time))
        paths = 0
        for output_variable, conjunctions in self.conjunctions.items():
            paths += len(conjunctions)
        config.log.add("Paths: {}".format(paths))
        if equivalent:
            print("Equivalent.")
        else:
            print("Not equivalent.")
        print("Stopped CHECK")
        print()
        return equivalent

    def is_equivalent(self, sampling_size: int = -1) -> bool:
        """
        Based on: https://www.usna.edu/Users/cs/wcbrown/courses/S18SI335/lec/l15/lec.html
        DFSVisit(vertex u)
          color u gray
          for each neighbor v of u do
            if v is white
              DFSVisit(v)
          color u black

        DFS(graph G)
          set the color of all vertices in G to white
          for each vertex u in G do
            if u is white
              DFSVisit(u)

        :param sampling_size:
        :return: Returns true if and only if the given Boolean function and specification are equivalent.

        """
        print("Started CHECK")
        self.start_time = time.time()

        # TODO: Fix multiple crossbars, i.e. a topology
        crossbar = self.boolean_function

        assert isinstance(crossbar, MemristorCrossbar)
        assert isinstance(self.specification, VerilogBenchmark)

        # # Construct a bipartite graph where the rows and columns are nodes, and the intersections are edges.
        # TODO: Change from literal attribute to (atom, positive) attributes
        graph = Graph()
        for layer in range(crossbar.layers):
            for r in range(crossbar.rows):
                for c in range(crossbar.columns):
                    memristor = crossbar.get_memristor(r, c, layer)
                    if memristor.literal != LITERAL('False', False):
                        if layer % 2 == 0:
                            graph.add_edge("L{}_{}".format(layer, r), "L{}_{}".format(layer + 1, c),
                                           literal=memristor.literal)
                        else:
                            graph.add_edge("L{}_{}".format(layer, c), "L{}_{}".format(layer + 1, r),
                                           literal=memristor.literal)

        for (input_function, (input_layer, input_nanowire)) in crossbar.get_input_nanowires().items():
            attrs = dict()
            for l in range(crossbar.layers + 1):
                if l % 2 == 0:
                    for r in range(crossbar.rows):
                        if l == input_layer and r == input_nanowire:
                            attrs["L{}_{}".format(l, r)] = {"output": False, "output_variables": set(), "visited": set(), "color": Color.white}
                        else:
                            attrs["L{}_{}".format(l, r)] = {"output": False, "output_variables": set(), "visited": set(), "color": Color.white}
                else:
                    for c in range(crossbar.columns):
                        if l == input_layer and c == input_nanowire:
                            attrs["L{}_{}".format(l, c)] = {"output": False, "output_variables": set(), "visited": set(), "color": Color.white}
                        else:
                            attrs["L{}_{}".format(l, c)] = {"output": False, "output_variables": set(), "visited": set(), "color": Color.white}
            set_node_attributes(graph, attrs)

            for (output_function, (output_layer, output_nanowire)) in crossbar.get_output_nanowires().items():
                graph.nodes["L{}_{}".format(output_layer, output_nanowire)]["output"] = True
                graph.nodes["L{}_{}".format(output_layer, output_nanowire)]["output_variables"].add(output_function)

            # graph.add_node("ROOT", **{"output": False, "output_variables": set(), "visited": set(), "color": Color.white})
            # graph.add_edge("ROOT", "L{}_{}".format(input_layer, input_nanowire), literal=LITERAL("True", True))
            # start_node = "ROOT"
            start_node = "L{}_{}".format(input_layer, input_nanowire)
            if not self._dfs_visit(graph, start_node):
                return self._halt(False)

            # We verify for each output variable whether the specification entails the extracted function.
            for output_function in crossbar.get_output_variables():
                sentence_a = Or(self.conjunctions.get(output_function))
                sentence_b = Z3Converter.verilog_to_z3(self.specification.verilog.functions.get(output_function).verilog_module)
                # if not self._entails(sentence_b, sentence_a):
                #     return self._halt(False)
                f = sentence_a == sentence_b
                s = Solver()
                s.add(Not(f))
                if s.check() != unsat:
                    return self._halt(False)

            return self._halt(True)

    def to_formula(self, output_variable: str) -> Bool:
        pass
