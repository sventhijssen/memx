from networkx import Graph

from utils import config
from core.expressions.BooleanExpression import LITERAL
from core.hardware.Crossbar import MemristorCrossbar


class CrossbarMapping2D:

    def __init__(self, graph: Graph):
        self.graph = graph
        self.vertical = []
        self.horizontal = []
        self.crossbar = None
        self.log = ''

    def map(self, vh_labeling: dict) -> MemristorCrossbar:
        self._node_assignment(vh_labeling)
        self._edge_assignment()
        self.crossbar.flip_vertical()
        # for i in range(len(self.crossbar.output_nanowires)):
        #     output_variable = list(self.crossbar.output_nanowires.keys())[i]
        #     self.crossbar.swap_rows(i, self.crossbar.output_nanowires[output_variable])
        return self.crossbar

    def _node_assignment(self, vh_labeling):
        for node in self.graph.nodes:
            if vh_labeling[node] == 1:
                self.vertical.append(node)
            elif vh_labeling[node] == -1:
                self.horizontal.append(node)
            else:
                self.vertical.append(node)
                self.horizontal.append(node)
        rows = len(self.horizontal)
        columns = len(self.vertical)
        config.log.add('Rows: {}\n'.format(rows))
        config.log.add('Columns: {}\n'.format(columns))
        self.crossbar = MemristorCrossbar(rows, columns)

    def _edge_assignment(self):
        input_variables = set()
        input_nodes = dict()
        root_nodes = dict()
        visited_nodes = set()
        for node_a, node_b in self.graph.edges:
            if not self.graph.nodes[node_a]["terminal"]:
                input_variables.add(self.graph.nodes[node_a]["variable"])
            if not self.graph.nodes[node_b]["terminal"]:
                input_variables.add(self.graph.nodes[node_b]["variable"])
            visited_nodes.add(node_a)
            visited_nodes.add(node_b)
            if config.io_constraints:
                if self.graph.nodes[node_a]["terminal"]:
                    input_variable = self.graph.nodes[node_a]["variable"]
                    input_nodes[input_variable] = self.horizontal.index(node_a)
                if self.graph.nodes[node_b]["terminal"]:
                    input_variable = self.graph.nodes[node_b]["variable"]
                    input_nodes[input_variable] = self.horizontal.index(node_b)
                if self.graph.nodes[node_a]["root"]:
                    output_variables = self.graph.nodes[node_a]["output_variables"]
                    for output_variable in output_variables:
                        root_nodes[output_variable] = self.horizontal.index(node_a)
                if self.graph.nodes[node_b]["root"]:
                    output_variables = self.graph.nodes[node_b]["output_variables"]
                    for output_variable in output_variables:
                        root_nodes[output_variable] = self.horizontal.index(node_b)

            edge_data = self.graph.get_edge_data(node_a, node_b)
            literal = edge_data.get("literal")
            # if variable is not None and positive is not None:
            #     literal = LITERAL(variable, positive)

            if node_a in self.horizontal and node_a in self.vertical:
                if node_b in self.horizontal:
                    r = self.horizontal.index(node_b)
                    c = self.vertical.index(node_a)
                else:
                    r = self.horizontal.index(node_a)
                    c = self.vertical.index(node_b)
                self.crossbar.set_memristor(r, c, literal)

                r = self.horizontal.index(node_a)
                c = self.vertical.index(node_a)
                self.crossbar.set_memristor(r, c, LITERAL('True', True))
            elif node_b in self.horizontal and node_b in self.vertical:
                if node_a in self.horizontal:
                    r = self.horizontal.index(node_a)
                    c = self.vertical.index(node_b)
                else:
                    r = self.horizontal.index(node_b)
                    c = self.vertical.index(node_a)
                self.crossbar.set_memristor(r, c, literal)

                r = self.horizontal.index(node_b)
                c = self.vertical.index(node_b)
                self.crossbar.set_memristor(r, c, LITERAL('True', True))
            elif node_a in self.horizontal and node_b in self.vertical:
                r = self.horizontal.index(node_a)
                c = self.vertical.index(node_b)
                self.crossbar.set_memristor(r, c, literal)
            else:
                r = self.horizontal.index(node_b)
                c = self.vertical.index(node_a)
                self.crossbar.set_memristor(r, c, literal)

        unvisited_nodes = set(self.graph.nodes) - visited_nodes

        for node in unvisited_nodes:
            if self.graph.nodes[node]["root"]:
                output_variables = self.graph.nodes[node]["output_variables"]
                for output_variable in output_variables:
                    root_nodes[output_variable] = self.horizontal.index(node)

        self.crossbar.input_variables = list(input_variables)
        for (input_function, nanowire) in input_nodes.items():
            self.crossbar.set_input_nanowire(input_function, nanowire)
        # self.crossbar.input_nanowires = dict(sorted(input_nodes.items()))
        for (output_function, nanowire) in root_nodes.items():
            self.crossbar.set_output_nanowire(output_function, nanowire)
        # self.crossbar.output_nanowires = dict(sorted(root_nodes.items()))
