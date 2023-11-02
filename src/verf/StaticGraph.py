from typing import List

import networkx
from networkx import Graph
from z3 import Bool

from core.benchmarks.Benchmark import VerilogBenchmark
from core.expressions.BooleanExpression import LITERAL
from core.hardware.Crossbar import MemristorCrossbar
from verf.GraphBasedEquivalenceChecker import GraphBasedEquivalenceChecker
from utils.Z3Converter import Z3Converter


class StaticGraph(GraphBasedEquivalenceChecker):

    def __init__(self, crossbar: MemristorCrossbar, specification: VerilogBenchmark):
        super().__init__(crossbar, specification)

    def get_simple_paths(self, output_variable: str) -> List[List[str]]:
        return self.simple_paths[output_variable]

    def to_formula(self, output_variable: str, input_function: str = "1") -> Bool:
        assert isinstance(self.boolean_function, MemristorCrossbar)

        # Construct a bipartite graph where the rows and columns are nodes, and the intersections are edges.
        graph = Graph()
        edge_node_mapping = dict()
        for layer in range(self.boolean_function.layers):
            for r in range(self.boolean_function.rows):
                for c in range(self.boolean_function.columns):
                    memristor = self.boolean_function.get_memristor(r, c, layer)
                    if memristor.literal != LITERAL('False', False):
                        if layer % 2 == 0:
                            graph.add_edge("L_{}_{}".format(layer, r), "L_{}_{}".format(layer + 1, c),
                                           literal=memristor.literal)
                            edge_node_mapping[("L{}_{}".format(layer, r), "C{}".format(layer + 1, c))] = str(memristor.literal)
                        else:
                            graph.add_edge("L_{}_{}".format(layer, c), "L_{}_{}".format(layer + 1, r),
                                           literal=memristor.literal)
                            edge_node_mapping[("L{}_{}".format(layer, c), "C{}".format(layer + 1, r))] = str(memristor.literal)

        # for r in range(self.crossbar.rows):
        #     for c in range(self.crossbar.columns):
        #         memristor = self.crossbar.get_memristor(r, c)
        #         if memristor.literal != LITERAL('False', False):
        #             graph.add_edge("R{}".format(r), "C{}".format(c))
        #             edge_node_mapping[("R{}".format(r), "C{}".format(c))] = str(memristor.literal)

        input_layer, input_nanowire = self.boolean_function.get_input_nanowire(input_function)
        output_layer, output_nanowire = self.boolean_function.get_output_nanowire(output_variable)

        # Start a breadth-first search on a dynamic graph
        start_node = "L_{}_{}".format(output_layer, output_nanowire)
        end_node = "L_{}_{}".format(input_layer, input_nanowire)
        # start_node = "R{}".format(self.crossbar.output_nanowires[output_variable])
        # end_node = "R{}".format(self.crossbar.input_nanowires[input_nanowire])

        # Verify whether the required input nanowire and output nanowire are in the graph
        if start_node not in graph.nodes or end_node not in graph.nodes:
            return False

        paths = list(networkx.all_simple_edge_paths(graph, end_node, start_node))
        simple_paths = []
        for path in paths:
            simple_path = []
            for (u, v) in path:
                if (u, v) in edge_node_mapping:
                    simple_path.append(edge_node_mapping[(u, v)])
                else:
                    simple_path.append(edge_node_mapping[(v, u)])
            simple_paths.append(simple_path)

        self.simple_paths[output_variable] = simple_paths

        formula = Z3Converter.simple_paths_to_z3(simple_paths)
        self.formulae[output_variable] = formula

        return formula
