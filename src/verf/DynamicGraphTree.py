import networkx
from networkx import MultiGraph, Graph
from z3 import Not, Bool, Or, And

from utils import config
from core.benchmarks.Benchmark import VerilogBenchmark
from core.expressions.BooleanExpression import LITERAL
from core.hardware.Crossbar import MemristorCrossbar
from verf.TreeBasedEquivalenceChecker import TreeBasedEquivalenceChecker


class Tree:

    def __init__(self, graph: Graph, node, parent, path):
        self.graph = graph
        self.node = node
        self.parent = parent
        self.parent_literal = None
        self.path = path
        self.children = dict()

    def build(self):
        graph = self.graph
        # self.plot(graph)
        current_node = self.node

        # Consider all the neighboring nodes of the current node
        for neighbor_node in graph.neighbors(current_node):
            outgoing_edges = graph.get_edge_data(current_node, neighbor_node)

            for key in outgoing_edges.keys():
                subgraph = graph.copy()

                outgoing_edge = outgoing_edges[key]
                literal = outgoing_edge["literal"]

                subgraph.remove_node(current_node)

                # Edges with negated selectorlines
                negated_edges = [(u, v, k) for u, v, k, d in subgraph.edges(data=True, keys=True) if d['literal'] == literal.negate()]

                # Remove edges with negated selectorlines
                for (u, v, k) in negated_edges:
                    subgraph.remove_edge(u, v, k)

                # Edges with idempotent (same) selectorlines
                idempotent_edges = [(u, v, k) for u, v, k, d in subgraph.edges(data=True, keys=True) if
                                    d['literal'] == literal]

                while len(idempotent_edges) != 0:
                    (u, v, k) = idempotent_edges[0]

                    # We cannot remove the neighbor node, considering we loop over the neighbors
                    if u == neighbor_node:
                        victim = v
                        victim_prime = u
                    else:
                        victim = u
                        victim_prime = v
                    victim_attr = subgraph.nodes[victim]
                    # If the victim is an output node, we pass this property to the node into which the victim merges
                    if victim_attr["output"]:
                        subgraph.nodes[victim_prime]["output"] = True
                    subgraph_copy = subgraph.copy()

                    # Let u be the victim, i.e. the node to be removed such that all its edges are connected to v
                    victim_neighbors = list(subgraph_copy.neighbors(victim))
                    subgraph_copy.remove_node(victim)
                    for victim_neighbor in victim_neighbors:
                        if victim_neighbor != victim_prime:
                            outgoing_edges_sub = subgraph.get_edge_data(victim, victim_neighbor)
                            for key_sub in outgoing_edges_sub.keys():
                                outgoing_edge_sub = outgoing_edges_sub[key_sub]
                                literal_sub = outgoing_edge_sub["literal"]
                                subgraph_copy.add_edge(victim_neighbor, victim_prime, literal=literal_sub)
                    idempotent_edges = [(x, y, k) for x, y, k, d in subgraph_copy.edges(data=True, keys=True) if
                                        d['literal'] == literal]

                    subgraph = subgraph_copy

                # The neighbor node has the output property. Hence, we can terminate this path
                # if subgraph.nodes[neighbor_node]["output"]:
                path = self.path.copy()
                path.append(literal)
                tree_child = Tree(subgraph, neighbor_node, self, path)
                tree_child.parent_literal = literal
                if neighbor_node in self.children:
                    self.children[neighbor_node].append({"output": subgraph.nodes[neighbor_node]["output"], "path": path, "subtree": tree_child})
                else:
                    self.children[neighbor_node] = [{"output": subgraph.nodes[neighbor_node]["output"], "path": path, "subtree": tree_child}]

        for child_key in self.children.keys():
            child_nodes = self.children[child_key]
            for child_node in child_nodes:
                if not child_node["output"]:
                    child_node["subtree"].build()


class DynamicGraphTree(TreeBasedEquivalenceChecker):

    def __init__(self, crossbar: MemristorCrossbar, specification: VerilogBenchmark):
        super().__init__(crossbar, specification)
        config.log.add("Verification method: CHECK\n")
        config.log.add("Static/dynamic: dynamic\n")

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
                            graph.add_edge("L{}_{}".format(layer, r), "L{}_{}".format(layer + 1, c),
                                           literal=memristor.literal)
                        else:
                            graph.add_edge("L{}_{}".format(layer, c), "L{}_{}".format(layer + 1, r),
                                           literal=memristor.literal)

        input_layer, input_nanowire = self.boolean_function.get_input_nanowire(input_function)
        output_layer, output_nanowire = self.boolean_function.get_output_nanowire(output_variable)

        # Verify whether the required input nanowire and output nanowire are in the graph
        if "L{}_{}".format(input_layer, input_nanowire) not in graph.nodes or "L{}_{}".format(output_layer, output_nanowire) not in graph.nodes:
            self.trees[output_variable] = None
            return False

        attrs = dict()
        # TODO: All input nanowires
        for l in range(self.boolean_function.layers + 1):
            if l % 2 == 0:
                for r in range(self.boolean_function.rows):
                    if l == input_layer and r == input_nanowire:
                        attrs["L{}_{}".format(l, r)] = {"output": True}
                    else:
                        attrs["L{}_{}".format(l, r)] = {"output": False}
            else:
                for c in range(self.boolean_function.columns):
                    if l == input_layer and c == input_nanowire:
                        attrs["L{}_{}".format(l, c)] = {"output": True}
                    else:
                        attrs["L{}_{}".format(l, c)] = {"output": False}
        networkx.set_node_attributes(graph, attrs)

        # Start a breadth-first search on a dynamic graph
        start_node = "L{}_{}".format(output_layer, output_nanowire)

        # For the dynamic graph, we use a tree for bookkeeping
        tree = Tree(graph, start_node, None, [])
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
