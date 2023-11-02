import networkx
from networkx import MultiGraph, Graph
from z3 import Not, Bool, Or, And

from utils import config
from core.benchmarks.Benchmark import VerilogBenchmark
from core.expressions.BooleanExpression import LITERAL
from core.hardware.Crossbar import MemristorCrossbar
from verf.TreeBasedEquivalenceChecker import TreeBasedEquivalenceChecker


class Tree:

    def __init__(self, graph: Graph, node, visited, parent, path):
        self.graph = graph
        self.node = node
        self.parent = parent
        self.parent_literal = None
        self.path = path
        self.visited = visited
        self.visited.add(node)
        self.children = dict()

    def build(self):
        graph = self.graph
        current_node = self.node

        # Consider all the neighboring nodes of the current node
        for neighbor_node in graph.neighbors(current_node):
            outgoing_edges = graph.get_edge_data(current_node, neighbor_node)
            if neighbor_node in self.visited:
                continue

            for key in outgoing_edges.keys():
                outgoing_edge = outgoing_edges[key]
                literal = outgoing_edge["literal"]
                path = self.path.copy()
                path.append(literal)
                tree_child = Tree(self.graph, neighbor_node, self.visited.copy(), self, path)
                tree_child.parent_literal = literal
                if neighbor_node in self.children:
                    self.children[neighbor_node].append({"output": self.graph.nodes[neighbor_node]["output"], "path": path, "subtree": tree_child})
                else:
                    self.children[neighbor_node] = [{"output": self.graph.nodes[neighbor_node]["output"], "path": path, "subtree": tree_child}]

        for child_key in self.children.keys():
            child_nodes = self.children[child_key]
            for child_node in child_nodes:
                if not child_node["output"]:
                    child_node["subtree"].build()


class StaticGraphTree(TreeBasedEquivalenceChecker):

    def __init__(self, crossbar: MemristorCrossbar, specification: VerilogBenchmark):
        super().__init__(crossbar, specification)
        config.log.add("Verification method: CHECK\n")
        config.log.add("Static/dynamic: static\n")

    def to_formula(self, output_variable: str, input_function: str = "1") -> Bool:
        assert isinstance(self.boolean_function, MemristorCrossbar)

        # Construct a bipartite graph where the rows and columns are nodes, and the intersections are edges.
        graph = MultiGraph()
        for layer in range(self.boolean_function.layers):
            for r in range(self.boolean_function.rows):
                for c in range(self.boolean_function.columns):
                    memristor = self.boolean_function.get_memristor(r, c, layer)
                    if memristor.literal != LITERAL('False', False):
                        if layer % 2 == 0:
                            graph.add_edge("L_{}_{}".format(layer, r), "L_{}_{}".format(layer + 1, c),
                                           literal=memristor.literal)
                        else:
                            graph.add_edge("L_{}_{}".format(layer, c), "L_{}_{}".format(layer + 1, r),
                                           literal=memristor.literal)
        # for r in range(self.crossbar.rows):
        #     for c in range(self.crossbar.columns):
        #         memristor = self.crossbar.get_memristor(r, c)
        #         if memristor.literal != LITERAL('False', False):
        #             graph.add_edge("R{}".format(r), "C{}".format(c), literal=memristor.literal)

        input_layer, input_nanowire = self.boolean_function.get_input_nanowire(input_function)
        output_layer, output_nanowire = self.boolean_function.get_output_nanowire(output_variable)

        start_node = "L_{}_{}".format(output_layer, output_nanowire)
        end_node = "L_{}_{}".format(input_layer, input_nanowire)

        # # Verify whether the required input nanowire and output nanowire are in the graph
        # Verify whether the required input nanowire and output nanowire are in the graph
        if start_node not in graph.nodes or end_node not in graph.nodes:
            return False
        # if "R{}".format(self.crossbar.input_nanowires[input_nanowire]) not in graph.nodes or "R{}".format(self.crossbar.output_nanowires[output_variable]) not in graph.nodes:
        #     return False

        attrs = dict()
        # TODO: All input nanowires
        for layer in range(self.boolean_function.layers + 1):
            if layer % 2 == 0:
                for r in range(self.boolean_function.rows):
                    if r == self.boolean_function.get_input_nanowire(input_function)[1]:
                        attrs["L_{}_{}".format(layer, r)] = {"output": True}
                    else:
                        attrs["L_{}_{}".format(layer, r)] = {"output": False}
            else:
                for c in range(self.boolean_function.columns):
                    attrs["L_{}_{}".format(layer, c)] = {"output": False}
        networkx.set_node_attributes(graph, attrs)
        # for r in range(self.crossbar.rows):
        #     if r == self.crossbar.get_input_nanowire(input_function)[1]:
        #         attrs["R{}".format(r)] = {"output": True}
        #     else:
        #         attrs["R{}".format(r)] = {"output": False}
        # for c in range(self.crossbar.columns):
        #     attrs["C{}".format(c)] = {"output": False}
        # networkx.set_node_attributes(graph, attrs)

        # Start a breadth-first search on a dynamic graph
        # start_node = "R{}".format(self.crossbar.output_nanowires[output_variable])

        # For the dynamic graph, we use a tree for bookkeeping
        tree = Tree(graph, start_node, set(), None, [])
        tree.build()
        self.trees[output_variable] = tree

        return self._to_z3_formula(tree)

    def _to_z3_formula(self, tree: Tree) -> Bool:
        # Recursively build up the Boolean formula
        child_expressions = []
        for child_nodes in tree.children.values():
            for child_node in child_nodes:
                if child_node["output"]:
                    literal = child_node["subtree"].parent_literal
                    if literal != LITERAL("True", True):
                        if literal.positive:
                            child_expressions.append(Bool(literal.atom))
                        else:
                            child_expressions.append(Not(Bool(literal.atom)))
                    else:
                        child_expressions.append(True)
                else:
                    child_expressions.append(self._to_z3_formula(child_node["subtree"]))
        subtree_expression = Or(*child_expressions)
        if tree.parent_literal is None:
            return subtree_expression
        else:
            literal = tree.parent_literal
            if literal != LITERAL("True", True):
                if literal.positive:
                    literal_expression = Bool(literal.atom)
                else:
                    literal_expression = Not(Bool(literal.atom))
            else:
                literal_expression = True
            return And(literal_expression, subtree_expression)
