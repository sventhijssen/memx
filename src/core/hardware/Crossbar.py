from __future__ import annotations

import copy
import re
from abc import abstractmethod, ABC
from pathlib import Path
from typing import Dict, Tuple, Set, Any, List

import numpy as np
from networkx import Graph, set_node_attributes, connected_components, has_path

from core.BooleanFunction import BooleanFunction
from core.hardware.Component import Component
from core.hardware.Memristor import Memristor
from core.expressions.BooleanExpression import LITERAL, FALSE, TRUE


class Crossbar(Component, ABC):
    """
    An abstract class to represent a crossbar.
    """

    def __init__(self, rows: int, columns: int, layers: int = 1, name: str = None):
        """
        Constructs a crossbar with the given dimensions x, y, and optionally z.
        :param rows: The number of memristors along the input and output nanowires.
        :param columns: The number of memristors orthogonal to the input and output nanowires.
        :param layers: The number of layers of memristors. The number of layers of nanowires is equal to the number
        of layers of memristors plus one. By default, the number of layers = 1.
        """
        super().__init__(name)
        self.rows = rows
        self.columns = columns
        self.layers = layers
        self.input_nanowires = dict()
        self.output_nanowires = dict()
        self.matrix = [[[Memristor(r, c, FALSE(), l) for c in range(self.columns)] for r in range(self.rows)] for l in range(self.layers)]

    @staticmethod
    def get_file_extension() -> str:
        return "xbar"

    @staticmethod
    def _literal_representation(literal: LITERAL):
        if literal == LITERAL("True", True):
            return 1
        elif literal == LITERAL("False", False):
            return 0
        else:
            return literal

    @staticmethod
    def from_string(content: str) -> BooleanFunction:
        for line in content.splitlines(keepends=True):
            if line.startswith(".type"):
                _, xbar_type = line.split()
                if xbar_type == "selector":
                    return SelectorCrossbar.from_string(content)
                elif xbar_type == "memristor":
                    return MemristorCrossbar.from_string(content)
                else:
                    raise Exception("Unknown crossbar type.")
        raise Exception("No crossbar type defined.")

    @staticmethod
    def read(file_path: Path) -> BooleanFunction:
        with open(file_path, 'r') as f:
            content = f.read()
            return Crossbar.from_string(content)

    @abstractmethod
    def instantiate(self, instance: Dict) -> Crossbar:
        pass

    @abstractmethod
    def fix(self, atom: str, positive: bool) -> Crossbar:
        pass

    def get_input_nanowire(self, input_function: str) -> Tuple[int, int]:
        return self.input_nanowires[input_function]

    def get_input_nanowires(self) -> Dict[str, Tuple[int, int]]:
        """
        Returns a dictionary mapping the input of this crossbar to the input nanowires.
        An input nanowire is defined by a tuple of its layer and index.
        :return: A dictionary mapping an input (str) to a tuple of a layer (int) and an index (int).
        """
        return self.input_nanowires

    def get_output_nanowire(self, output_variable: str) -> Tuple[int, int]:
        """
        Returns the output nanowire of the given output variable.
        :param output_variable: The given output variable.
        :return: A tuple of the layer and the index.
        """
        return self.output_nanowires[output_variable]

    def get_output_nanowires(self) -> Dict[str, Tuple[int, int]]:
        """
        Returns a dictionary mapping the output variables of this crossbar to the output nanowire.
        An output nanowire is defined by a tuple of its layer and index.
        :return: A dictionary mapping an output variable (str) to a tuple of a layer (int) and an index (int).
        """
        return self.output_nanowires

    def set_input_nanowire(self, input_function: str, nanowire: int, layer: int = 0):
        self.input_nanowires[input_function] = (layer, nanowire)

    def set_output_nanowire(self, output_function: str, nanowire: int, layer: int = 0):
        self.output_nanowires[output_function] = (layer, nanowire)

    def graph(self, boolean_expression_representation: bool = False) -> Graph:
        """
        Returns a bipartite_graph representation based on the following analogy: nanowires in the crossbar correspond to nodes in the bipartite_graph, and memristors in the crossbar correspond to edges in the bipartite_graph.
        The resulting bipartite_graph is a multi-layered bipartite_graph. More specifically, the bipartite_graph is k-layered and bipartite.
        :param boolean_expression_representation: If true, the edge will be represented as a Boolean expression.
        Otherwise, as an atom and a truth value.
        :return: A k-layered bipartite bipartite_graph.
        """
        graph = Graph()
        for layer in range(self.layers):
            for r in range(self.rows):
                for c in range(self.columns):
                    memristor = self.get_memristor(r, c, layer=layer)
                    if layer % 2 == 0:
                        if boolean_expression_representation:
                            graph.add_edge("L{}_{}".format(layer, r), "L{}_{}".format(layer + 1, c),
                                           boolean_expression=memristor.literal)
                        else:
                            graph.add_edge("L{}_{}".format(layer, r), "L{}_{}".format(layer + 1, c),
                                           atom=memristor.literal.atom,
                                           positive=memristor.literal.positive)
                    else:
                        if boolean_expression_representation:
                            graph.add_edge("L{}_{}".format(layer, c), "L{}_{}".format(layer + 1, r),
                                           boolean_expression=memristor.literal)
                        else:
                            graph.add_edge("L{}_{}".format(layer, c), "L{}_{}".format(layer + 1, r),
                                           atom=memristor.literal.atom,
                                           positive=memristor.literal.positive)

        attributes = dict()
        for input_function, (layer, index) in self.get_input_nanowires().items():
            if "L{}_{}".format(layer, index) not in attributes:
                attributes["L{}_{}".format(layer, index)] = dict()
            attributes["L{}_{}".format(layer, index)]["input_function"] = input_function
        for output_function, (layer, index) in self.get_output_nanowires().items():
            if "L{}_{}".format(layer, index) not in attributes:
                attributes["L{}_{}".format(layer, index)] = dict()
            if "output_functions" not in attributes["L{}_{}".format(layer, index)]:
                attributes["L{}_{}".format(layer, index)]["output_functions"] = set()
            attributes["L{}_{}".format(layer, index)]["output_functions"].add(output_function)

        set_node_attributes(graph, attributes)

        return graph

    def find(self, literal: LITERAL) -> Set[Tuple[int, int, int]]:
        """
        Returns the positions of the given selectorlines occurring in this crossbar.
        :param literal: The given literal to find in this crossbar.
        :return: A list of positions (tuples) at which the literal occurs.
        """
        positions = set()
        for l in range(self.layers):
            for r in range(self.rows):
                for c in range(self.columns):
                    if self.get_memristor(r, c, layer=l).literal == literal:
                        positions.add((l, r, c))
        return positions

    def get_rows(self) -> int:
        """
        Returns the number of rows of this crossbar.
        :return: The number of rows of this crossbar.
        """
        return self.rows

    def get_columns(self) -> int:
        """
        Returns the number of columns of this crossbar.
        :return: The number of columns of this crossbar.
        """
        return self.columns

    def get_nanowire_layers(self) -> int:
        """
        Returns the number of layers (nanowires) of this crossbar.
        :return: The number of layers of nanowires in this crossbar.
        """
        return self.layers + 1

    def get_memristor_layers(self) -> int:
        """
        Returns the number of layers (memristors) of this crossbar.
        :return: The number of layers of memristors in this crossbar.
        """
        return self.layers

    def get_semiperimeter(self):
        """
        Returns the semiperimeter (number of wordlines + number of bitlines)
        of this crossbar.
        :return: The semiperimeter of this crossbar.
        """
        return self.get_rows() + self.get_columns()

    def get_area(self):
        """
        Returns the area (number of wordlines * number of bitlines) of this crossbar.
        :return: The area of this crossbar.
        """
        return self.get_rows() * self.get_columns()

    def get_volume(self):
        """
        Returns the volume (area * number of layers of memristors) of this crossbar.
        :return: The number of layers of this crossbar.
        """
        return self.get_area() * self.get_memristor_layers()

    def get_memristor(self, row: int, column: int, layer: int = 0) -> Memristor:
        """
        Returns the memristor at the given row and column.
        :param row: The given row in this crossbar.
        :param column: The given column in this crossbar.
        :param layer: The given layer in this crossbar.
        :return: The memristor at the given row and column.
        """
        return self.matrix[layer][row][column]

    def set_memristor(self, row: int, column: int, literal: LITERAL, layer: int = 0, stuck_at_fault: bool = False):
        """
        Assigns the given literal to the memristor at the given row and column.
        :param row: The given row in this crossbar.
        :param column: The given column in this crossbar.
        :param literal: The given literal to be assigned.
        :param layer: The given layer in this crossbar.
        :param stuck_at_fault:
        :return:
        """
        memristor = Memristor(row, column, literal, layer)
        self.matrix[layer][row][column] = memristor

    def flip_horizontal(self, layer: int = 0):
        """
        Flips the nanowire over its axis parallel to the nanowires in its layer (i.e. mirrors).
        :return:
        """
        self.matrix.reverse()

        for r in range(self.rows):
            for c in range(self.columns):
                memristor = self.get_memristor(r, c, layer=layer)
                self.set_memristor(r, c, memristor.literal, layer)

        outputs = dict()
        for (output_variable, (layer, row)) in self.get_output_nanowires().items():
            outputs[output_variable] = self.rows - 1 - row
        self.output_nanowires = outputs

    def flip_vertical(self):
        """
        Flips the nanowire of its axis parallel to the nanowires in its layer (i.e. mirrors).
        :param layer:
        :return:
        """
        for layer in range(self.layers):
            for r in range(self.rows):
                old_row = self.matrix[layer][r]
                new_row = old_row[::-1]
                for c in range(self.columns):
                    literal = new_row[c].literal
                    new_row[c] = Memristor(r, c, literal, layer)
                self.matrix[layer][r] = new_row


class MemristorCrossbar(Crossbar):
    """
    Type of crossbar where are assigned to memristors.
    """

    def __init__(self, rows: int, columns: int, layers: int = 1, name: str = None):
        """
        Constructs a memristor crossbar of dimensions (number of memristors) x by y.
        The optional dimension layers indicates the number of layers of memristors.
        By default, the number of layers is 1.
        A memristor is defined by a triple (l, r, c) where r is the index of the nanowire below the memristor,
        c is the index of the nanowire above the memristor, and l is the layer of the memristor.
        A nanowire is defined by a tuple (l, i) where i is the index in a series of parallel nanowires at layer l.
        :param rows: The number of memristors along the input and output nanowires.
        :param columns: The number of memristors orthogonal to the input and output nanowires.
        :param layers: The number of layers of memristors.
        """
        super(MemristorCrossbar, self).__init__(rows, columns, layers, name)

    def get_input_variables(self) -> Set[str]:
        input_variables = set()
        for l in range(self.layers):
            for r in range(self.rows):
                for c in range(self.columns):
                    memristor = self.get_memristor(r, c, l)
                    literal = memristor.literal
                    if literal != TRUE() and literal != FALSE():
                        input_variables.add(literal.atom)
        return input_variables

    def get_output_variables(self) -> Set[str]:
        return set(self.output_nanowires.keys())

    def get_auxiliary_variables(self) -> Set[str]:
        return set()

    def get_log(self) -> Dict[str, Any]:
        graph = self.graph()
        return {
            "type": self.__class__.__name__,
            "rows": self.rows,
            "columns": self.columns,
            "layers": self.layers,
            "input_nanowires": len(self.input_nanowires),
            "output_nanowires": len(self.output_nanowires.items()),
            "bipartite_graph":
                {
                    "nodes": len(list(graph.nodes)),
                    "edges": len(list(graph.edges)),
                    "literals": len(list(filter(lambda e: graph.get_edge_data(e[0], e[1]).get("atom") != "False" and graph.get_edge_data(e[0], e[1]).get("atom") != "True", graph.edges))),
                    "on": len(list(filter(lambda e: graph.get_edge_data(e[0], e[1]).get("atom") == "True" and graph.get_edge_data(e[0], e[1]).get("positive") == True, graph.edges))),
                    "off": len(list(filter(lambda e: graph.get_edge_data(e[0], e[1]).get("atom") == "False" and graph.get_edge_data(e[0], e[1]).get("positive") == False, graph.edges))),
                }
        }

    @staticmethod
    def from_string(content: str) -> BooleanFunction:
        rows = 0
        columns = 0
        input_variables = None
        input_nanowires = dict()
        output_nanowires = dict()

        lines = content.splitlines(keepends=True)

        for line in lines:

            if line.startswith(".rows "):
                (_, raw_value) = line.split()
                rows = int(raw_value)

            elif line.startswith(".columns "):
                (_, raw_value) = line.split()
                columns = int(raw_value)

            elif line.startswith(".inputs "):
                raw_values = line.split()
                input_variables = set(raw_values[1:])

            elif line.startswith(".i "):
                raw_values = line.split()
                if len(raw_values) == 3:
                    input_nanowires[raw_values[1]] = (0, int(raw_values[2]))
                elif len(raw_values) == 4:
                    input_nanowires[raw_values[1]] = (int(raw_values[2]), int(raw_values[3]))
                else:
                    raise Exception("Length incorrect.")

            elif line.startswith(".o "):
                raw_values = line.split()
                if len(raw_values) == 3:
                    output_nanowires[raw_values[1]] = (0, int(raw_values[2]))
                elif len(raw_values) == 4:
                    output_nanowires[raw_values[1]] = (int(raw_values[2]), int(raw_values[3]))
                else:
                    raise Exception("Length incorrect.")

        crossbar = MemristorCrossbar(rows, columns)
        crossbar.input_variables = input_variables
        crossbar.input_nanowires = input_nanowires
        crossbar.output_nanowires = output_nanowires

        r = 0
        c = 0
        read = False
        for line in lines:

            if line.startswith(".end"):
                read = False

            if read:
                for element in line.split("\t"):
                    raw_literal = re.findall(r'(-|0|1|[\[\]a-z0-9]+|~[\[\]a-z0-9]+)', element)[0]
                    if raw_literal == '0':
                        crossbar.set_memristor(r, c, LITERAL('False', False))
                    elif raw_literal == '1':
                        crossbar.set_memristor(r, c, LITERAL('True', True))
                    elif raw_literal[0] == '~':
                        crossbar.set_memristor(r, c, LITERAL(raw_literal[1:], False))
                    else:
                        crossbar.set_memristor(r, c, LITERAL(raw_literal, True))
                    c += 1
                c = 0
                r += 1

            if line.startswith(".xbar"):
                read = True

        return crossbar

    def to_string(self) -> str:
        content = ""
        content += ".model {}\n".format(self.get_name())
        content += ".type memristor\n"
        content += ".inputs {}\n".format(' '.join(self.get_input_variables()))
        content += ".outputs {}\n".format(' '.join(self.get_output_variables()))
        content += ".rows {}\n".format(self.rows)
        content += ".columns {}\n".format(self.columns)
        for (input_variable, (layer, nanowire)) in self.get_input_nanowires().items():
            if layer == 0:
                content += ".i {} {}\n".format(input_variable, nanowire)
            else:
                content += ".i {} {} {}\n".format(input_variable, layer, nanowire)
        for (output_variable, (layer, nanowire)) in self.get_output_nanowires().items():
            if layer == 0:
                content += ".o {} {}\n".format(output_variable, nanowire)
            else:
                content += ".o {} {} {}\n".format(output_variable, layer, nanowire)
        content += ".xbar\n"
        for r in range(self.rows):
            for c in range(self.columns):
                literal = self._literal_representation(self.get_memristor(r, c).literal)
                if c < self.columns - 1:
                    content += "{}\t".format(literal)
                else:
                    content += "{}\r\n".format(literal)
        content += ".end\n"
        return content

    def to_dot(self) -> str:

        # TODO: Support crossbars with multiple layers in the future.
        assert self.get_memristor_layers() == 1

        layer = 0

        # Grid after https://graphviz.org/Gallery/undirected/grid.html
        # Node distance after https://newbedev.com/how-to-manage-distance-between-nodes-in-graphviz
        content = ''
        content += 'graph {} {{\n'.format(self.name)
        content += '\tgraph [nodesep="0.2", ranksep="0.2"];\n'
        content += '\tcharset="UTF-8";\n'
        content += '\tratio=fill;\n'
        content += '\tsplines=polyline;\n'
        content += '\toverlap=scale;\n'
        content += '\tnode [shape=circle, fixedsize=true, width=0.4, fontsize=8];\n'
        content += '\n'

        content += '\n\t// Memristors\n'
        for c in range(self.columns):
            for r in range(self.rows):
                if self.get_memristor(r, c, layer).literal.atom == 'False':
                    v = '0'
                    style = 'color="#000000", fillcolor="#eeeeee", style="filled,solid"'
                elif self.get_memristor(r, c, layer).literal.atom == 'True':
                    v = '1'
                    style = 'color="#000000", fillcolor="#cadfb8", style="filled,solid"'
                else:
                    if not self.get_memristor(r, c, layer).literal.positive:
                        v = '¬' + self.get_memristor(r, c, layer).literal.atom
                    else:
                        v = self.get_memristor(r, c, layer).literal.atom
                    style = 'color="#000000", fillcolor="#b4c7e7", style="filled,solid"'
                content += '\tm{}_{} [label="{}" {}]\n'.format(r + 1, c + 1, v, style)

        content += '\n\t// Functions (left y-axis)\n'
        # Functions
        for r in range(self.rows):
            input_rows = list(map(lambda i: i[1], self.get_input_nanowires().values()))
            style = 'color="#ffffff", fillcolor="#ffffff", style="filled,solid"'
            if r not in input_rows:
                v = ''  # '{}'.format(self.wordlines[r][0])
                content += '\tm{}_{} [label="{}" {}]\n'.format(r + 1, 0, v, style)
            else:
                v = ''
                for (input_function, (layer, row)) in self.get_input_nanowires().items():
                    if r == row:
                        v = 'Vin<SUB>{}</SUB>'.format(input_function)
                content += '\tm{}_{} [label=<{}> {}]\n'.format(r + 1, 0, v, style)

        content += '\n\t// Outputs (right y-axis)\n'
        # Outputs
        output_variables = dict()
        for (o, (l, r)) in self.output_nanowires.items():
            if (l, r) in output_variables:
                output_variables[(l, r)].append(o)
            else:
                output_variables[(l, r)] = [o]
        for ((l, r), os) in output_variables.items():
            if layer == l:
                for i in range(len(os)):
                    v = os[i]
                    style = 'color="#ffffff", fillcolor="#ffffff", style="filled,solid"'
                    content += '\tm{}_{} [label="{}" {}];\n'.format(r + 1, self.columns + 1, v, style)

        content += '\n\t// Crossbar\n'
        # Important: The description of the grid is transposed when being rendered -> rows and columns are switched
        for r in range(self.rows):
            input_rows = list(map(lambda i: i[1], self.get_input_nanowires().values()))
            content += '\trank=same {\n'
            for c in range(self.columns):
                if r not in input_rows and c == 0:
                    content += '\t\tm{}_{} -- m{}_{} [style=invis];\n'.format(r + 1, c, r + 1, c + 1)
                else:
                    content += '\t\tm{}_{} -- m{}_{};\n'.format(r + 1, c, r + 1, c + 1)

            # TODO: Change layer
            if (0, r) in output_variables:
                content += '\t\tm{}_{} -- m{}_{};\n'.format(r + 1, self.columns, r + 1, self.columns + 1)
            content += '\t}\n'

        for c in range(self.columns):
            content += '\t' + ' -- '.join(["m{}_{}".format(r + 1, c + 1) for r in range(self.rows)]) + '\n'

        content += '}'
        return content

    def __copy__(self):
        crossbar = MemristorCrossbar(self.rows, self.columns, self.layers)
        crossbar.matrix = copy.deepcopy(self.matrix)
        crossbar.input_nanowires = self.input_nanowires
        crossbar.output_nanowires = self.output_nanowires.copy()
        return crossbar

    def fix(self, atom: str, positive: bool) -> MemristorCrossbar:
        crossbar = copy.deepcopy(self)
        for l in range(self.layers):
            for r in range(self.rows):
                for c in range(self.columns):
                    memristor = self.get_memristor(r, c, l)
                    literal = memristor.literal
                    crossbar.set_memristor(r, c, literal.fix(atom, positive), l)
        return crossbar

    def find_equivalent_components(self) -> List:
        graph = self.graph()
        o_non_one_edges = [(u, v) for u, v, d in graph.edges(data=True) if
                           not (d['atom'] == 'True' and d['positive'])]
        graph.remove_edges_from(o_non_one_edges)

        equivalent = [list(f) for f in connected_components(graph)]
        return equivalent

    @staticmethod
    def _find_equivalent_row_or_column(equivalent: List, layer: int) -> List[List[int]]:
        """
        The axis 0 denotes one axis, and the axis 1 denotes the perpendicular axis of nanowires.
        :param equivalent:
        :param axis:
        :return:
        """
        f = [list(map(lambda w: int(w[3:]), filter(lambda x: x[1] == str(layer), equivalent_subset))) for equivalent_subset in equivalent]
        return f

    def get_equivalent_rows(self) -> List[List[int]]:
        equivalent = self.find_equivalent_components()
        return self._find_equivalent_row_or_column(equivalent, 0)

    def get_equivalent_columns(self) -> List[List[int]]:
        equivalent = self.find_equivalent_components()
        return self._find_equivalent_row_or_column(equivalent, 1)

    def get_ternary_matrix(self, layer: int = 0) -> np.ndarray:
        """
        TODO: Adapt to handle all layers, currently only handles one layer (layer 0)
        :param layer:
        :return:
        """
        ternary_matrix = np.empty((self.rows, self.columns))
        for r in range(self.rows):
            for c in range(self.columns):
                if self.get_memristor(r, c).literal == TRUE():
                    ternary_matrix[r, c] = 1
                elif self.get_memristor(r, c).literal == FALSE():
                    ternary_matrix[r, c] = -1
                else:
                    ternary_matrix[r, c] = 0
        return ternary_matrix

    def compress(self) -> MemristorCrossbar:
        ternary_matrix = self.get_ternary_matrix()
        equivalent_rows = self.get_equivalent_rows()
        compressed_rows = self._compress_equivalent_rows(ternary_matrix, equivalent_rows)
        row_compressed_crossbar = MemristorCrossbar.nd_array_to_crossbar(compressed_rows, equivalent_rows)
        equivalent_columns = row_compressed_crossbar.get_equivalent_columns()
        compressed_columns = self._compress_equivalent_columns(compressed_rows, equivalent_columns)
        compressed_crossbar = MemristorCrossbar.nd_array_to_crossbar(compressed_columns, equivalent_columns)
        return compressed_crossbar

    @staticmethod
    def nd_array_to_crossbar(nd_array: np.ndarray, equivalent_dimension: List[List[int]]) -> MemristorCrossbar:
        crossbar = MemristorCrossbar(nd_array.shape[0], nd_array.shape[1])
        for r in range(nd_array.shape[0]):
            for c in range(nd_array.shape[1]):
                if nd_array[r, c] == 1:
                    crossbar.set_memristor(r, c, TRUE())
                elif nd_array[r, c] == -1:
                    crossbar.set_memristor(r, c, FALSE())
                else:
                    # TODO: Fix
                    crossbar.set_memristor(r, c, LITERAL("x", True))
        return crossbar

    @staticmethod
    def _compress_equivalent_rows(ternary_matrix: np.ndarray, equivalent_rows: List) -> np.ndarray:
        rows = []
        for group in equivalent_rows:
            if len(group) > 0:
                a = np.amax(np.array(list(map(lambda x: ternary_matrix[x, :], group))), axis=0)
                rows.append([a])
        if rows:
            n = np.concatenate(rows)
        else:
            n = ternary_matrix
        return n

    @staticmethod
    def _compress_equivalent_columns(ternary_matrix, equivalent_columns: List) -> np.ndarray:
        cols = []
        for group in equivalent_columns:
            if len(group) > 0:
                a = np.amax(np.array(list(map(lambda x: ternary_matrix[:, x], group))), axis=0)
                cols.append([a])
        if cols:
            n = np.concatenate(cols).transpose()
        else:
            n = ternary_matrix
        return n

    def transpose(self) -> MemristorCrossbar:
        crossbar = MemristorCrossbar(self.columns, self.rows)
        for r in range(self.rows):
            for c in range(self.columns):
                crossbar.set_memristor(c, r, self.get_memristor(r, c).literal)

        crossbar.input_nanowires = self.get_input_nanowires()
        crossbar.output_nanowires = self.get_output_nanowires()
        return crossbar

    def instantiate(self, instance: dict) -> MemristorCrossbar:
        for layer in range(self.layers):
            for r in range(self.rows):
                for c in range(self.columns):
                    memristor = self.get_memristor(r, c, layer)
                    literal = memristor.literal
                    variable_name = literal.atom
                    positive = literal.positive
                    if variable_name != "True" and variable_name != "False":
                        if not memristor.stuck_at_fault:
                            if positive:
                                if instance[variable_name]:
                                    literal = LITERAL('True', True)
                                else:
                                    literal = LITERAL('False', False)
                            else:
                                if instance[variable_name]:
                                    literal = LITERAL('False', False)
                                else:
                                    literal = LITERAL('True', True)
                            self.set_memristor(r, c, literal, layer=layer)
        return self

    def eval(self, instance: Dict[str, bool], input_function: str = "1") -> Dict[str, bool]:
        # For all input nanowires different from a different input function than the given input function,
        # we set the selectorlines False to avoid any loops through these nanowires.
        for (other_input_function, (layer, input_nanowire)) in self.get_input_nanowires().items():
            if input_function != other_input_function:
                for c in range(self.columns):
                    self.set_memristor(input_nanowire, c, FALSE(), layer=layer)

        crossbar_copy = self.__copy__()
        crossbar_instance = crossbar_copy.instantiate(instance)
        graph = crossbar_instance.graph()
        true_edges = [(u, v) for u, v, d in graph.edges(data=True) if
                              not (d['atom'] == 'True' and d['positive'])]
        graph.remove_edges_from(true_edges)

        evaluation = dict()
        for (output_variable, (output_layer, output_nanowire)) in crossbar_instance.get_output_nanowires().items():
            source = "L{}_{}".format(output_layer, output_nanowire)
            input_layer, input_nanowire = crossbar_instance.get_input_nanowire(input_function)
            sink = "L{}_{}".format(input_layer, input_nanowire)
            evaluation[output_variable] = has_path(graph, source, sink)

        return evaluation


class SelectorCrossbar(Crossbar):
    """
    Type of crossbar where selectorlines are assigned to nanowires.
    """

    def __init__(self, rows: int, columns: int, name: str = None):
        super().__init__(rows, columns, name=name)
        self.wordlines = []  # Nodes in BDD
        self.selectorlines = []  # Edges in BDD

    def get_input_variables(self) -> Set[str]:
        input_variables = set()
        for selectorline in self.selectorlines:
            if isinstance(selectorline, LITERAL):
                input_variables.add(selectorline.atom)
        return input_variables

    def get_output_variables(self) -> Set[str]:
        output_variables = set()
        for output_variable in self.get_output_nanowires().keys():
            output_variables.add(output_variable)
        return output_variables

    def get_auxiliary_variables(self) -> Set[str]:
        return set()

    def get_log(self) -> Dict:
        return {
            "id": id(self),
            "type":  self.__class__.__name__,
            "name": id(self),  # TODO: Fix name issues
            "rows": self.rows,
            "columns": self.columns,
            "wordlines": list(map(lambda func: str(func), self.wordlines)),
            "selectorlines": list(map(lambda lit: str(lit), self.selectorlines)),
            "layers": self.layers,
            "input_nanowires": self.input_nanowires,
            # A key maps to a set of values. However, JSON cannot encode a set, thus we convert it into a list.
            "output_nanowires": dict(map(lambda item: (item[0], list(item[1])), self.output_nanowires.items()))
        }

    def fix(self, atom: str, positive: bool) -> Crossbar:
        raise NotImplementedError()

    @staticmethod
    def from_string(content: str) -> BooleanFunction:
        rows = 0
        columns = 0
        input_variables = None
        input_nanowires = dict()
        output_nanowires = dict()
        selectorlines = []

        lines = content.splitlines(keepends=True)

        for line in lines:

            if line.startswith(".rows "):
                (_, raw_value) = line.split()
                rows = int(raw_value)

            elif line.startswith(".columns "):
                (_, raw_value) = line.split()
                columns = int(raw_value)

            elif line.startswith(".inputs "):
                raw_values = line.split()
                input_variables = set(raw_values[1:])

            elif line.startswith(".i "):
                raw_values = line.split()
                if len(raw_values) == 3:
                    input_nanowires[raw_values[1]] = (0, int(raw_values[2]))
                elif len(raw_values) == 4:
                    input_nanowires[raw_values[1]] = (int(raw_values[2]), int(raw_values[3]))
                else:
                    raise Exception("Length incorrect.")

            elif line.startswith(".o "):
                raw_values = line.split()
                if len(raw_values) == 3:
                    output_nanowires[raw_values[1]] = (0, int(raw_values[2]))
                elif len(raw_values) == 4:
                    output_nanowires[raw_values[1]] = (int(raw_values[2]), int(raw_values[3]))
                else:
                    raise Exception("Length incorrect.")

            elif line.startswith(".s "):
                raw_values = line.split()
                if len(raw_values) == 3:
                    raw_literal = raw_values[2]
                    if raw_literal.startswith("~"):
                        literal = LITERAL(raw_literal[1:], False)
                    else:
                        literal = LITERAL(raw_literal, True)
                    selectorlines.append(literal)
                else:
                    raise Exception("Length incorrect.")

        crossbar = SelectorCrossbar(rows, columns)
        crossbar.selectorlines = selectorlines
        crossbar.input_variables = input_variables
        crossbar.input_nanowires = input_nanowires
        crossbar.output_nanowires = output_nanowires

        r = 0
        c = 0
        read = False
        for line in lines:

            if line.startswith(".end"):
                read = False

            if read:
                for element in line.split("\t"):
                    raw_literal = re.findall(r'(-|0|1|[\[\]a-z0-9]+|~[\[\]a-z0-9]+)', element)[0]
                    if raw_literal == '0':
                        crossbar.set_memristor(r, c, LITERAL('False', False))
                    elif raw_literal == '1':
                        crossbar.set_memristor(r, c, LITERAL('True', True))
                    elif raw_literal[0] == '~':
                        crossbar.set_memristor(r, c, LITERAL(raw_literal[1:], False))
                    else:
                        crossbar.set_memristor(r, c, LITERAL(raw_literal, True))
                    c += 1
                c = 0
                r += 1

            if line.startswith(".xbar"):
                read = True

        return crossbar

    def to_string(self) -> str:
        content = ""
        content += ".model {}\n".format(self.get_name())
        content += ".type selector\n"
        content += ".inputs {}\n".format(' '.join(self.get_input_variables()))
        content += ".outputs {}\n".format(' '.join(self.get_output_variables()))
        content += ".rows {}\n".format(self.rows)
        content += ".columns {}\n".format(self.columns)
        for (input_variable, (layer, nanowire)) in self.get_input_nanowires().items():
            if layer == 0:
                content += ".i {} {}\n".format(input_variable, nanowire)
            else:
                content += ".i {} {} {}\n".format(input_variable, layer, nanowire)
        for (output_variable, (layer, nanowire)) in self.get_output_nanowires().items():
            if layer == 0:
                content += ".o {} {}\n".format(output_variable, nanowire)
            else:
                content += ".o {} {} {}\n".format(output_variable, layer, nanowire)
        for i in range(len(self.selectorlines)):
            literal = self.selectorlines[i]
            content += ".s {} {}\n".format(i, self._literal_representation(literal))
        content += ".xbar\n"
        for r in range(self.rows):
            for c in range(self.columns):
                literal = self._literal_representation(self.get_memristor(r, c).literal)
                if c < self.columns - 1:
                    content += "{}\t".format(literal)
                else:
                    content += "{}\r\n".format(literal)
        content += ".end\n"
        return content

    def to_dot(self) -> str:
        # Grid after https://graphviz.org/Gallery/undirected/grid.html
        # Node distance after https://newbedev.com/how-to-manage-distance-between-nodes-in-graphviz
        name = self.get_name()

        if self.get_memristor_layers() > 1:
            raise Exception("Only single memristor layer supported.")

        layer = 0
        content = ''
        content += 'graph {} {{\n'.format(name)
        content += '\tgraph [nodesep="0.2", ranksep="0.2"];\n'
        content += '\tcharset="UTF-8";\n'
        content += '\tratio=fill;\n'
        content += '\tsplines=polyline;\n'
        content += '\toverlap=scale;\n'
        content += '\tnode [shape=circle, fixedsize=true, width=0.4, fontsize=8];\n'
        content += '\n'

        content += '\n\t// Memristors\n'
        for c in range(self.columns):
            for r in range(self.rows):
                if self.get_memristor(r, c, layer).literal.atom == 'False':
                    v = '0'
                    style = 'color="#000000", fillcolor="#eeeeee", style="filled,solid"'
                elif self.get_memristor(r, c, layer).literal.atom == 'True':
                    v = '1'
                    style = 'color="#000000", fillcolor="#cadfb8", style="filled,solid"'
                else:
                    if not self.get_memristor(r, c, layer).literal.positive:
                        v = '¬' + self.get_memristor(r, c, layer).literal.atom
                    else:
                        v = self.get_memristor(r, c, layer).literal.atom
                    style = 'color="#000000", fillcolor="#b4c7e7", style="filled,solid"'
                content += '\tm{}_{} [label="{}" {}]\n'.format(r + 1, c + 1, v, style)

        content += '\n\t// Functions (left y-axis)\n'
        # Functions
        for r in range(len(self.wordlines)):
            input_rows = list(map(lambda i: i[1], self.get_input_nanowires().values()))
            style = 'color="#ffffff", fillcolor="#ffffff", style="filled,solid"'
            if r not in input_rows:
                v = '{}'.format(self.wordlines[r])
                content += '\tm{}_{} [label="{}" {}]\n'.format(r + 1, 0, v, style)
            else:
                v = ''
                for (input_function, (layer, row)) in self.get_input_nanowires().items():
                    if r == row:
                        v = 'Vin<SUB>{}</SUB>'.format(input_function)
                content += '\tm{}_{} [label=<{}> {}]\n'.format(r + 1, 0, v, style)
        for r in range(len(self.wordlines), self.rows):
            style = 'color="#ffffff", fillcolor="#ffffff", style="filled,solid"'
            v = ''
            content += '\tm{}_{} [label="{}" {}]\n'.format(r + 1, 0, v, style)

        content += '\n\t// Outputs (right y-axis)\n'
        # Outputs
        output_variables = dict()
        for (o, (l, r)) in self.output_nanowires.items():
            if (l, r) in output_variables:
                output_variables[(l, r)].append(o)
            else:
                output_variables[(l, r)] = [o]
        for ((l, r), os) in output_variables.items():
            if layer == l:
                for i in range(len(os)):
                    v = os[i]
                    style = 'color="#ffffff", fillcolor="#ffffff", style="filled,solid"'
                    content += '\tm{}_{} [label="{}" {}];\n'.format(r + 1, self.columns + 1, v, style)

        content += '\n\t// Crossbar\n'
        # Important: The description of the grid is transposed when being rendered -> rows and columns are switched
        for r in range(self.rows):
            input_rows = list(map(lambda i: i[1], self.get_input_nanowires().values()))
            content += '\trank=same {\n'
            for c in range(self.columns):
                if r not in input_rows and c == 0:
                    content += '\t\tm{}_{} -- m{}_{} [style=invis];\n'.format(r + 1, c, r + 1, c + 1)
                else:
                    content += '\t\tm{}_{} -- m{}_{};\n'.format(r + 1, c, r + 1, c + 1)

            # TODO: Change layer
            if (0, r) in output_variables:
                content += '\t\tm{}_{} -- m{}_{};\n'.format(r + 1, self.columns, r + 1, self.columns + 1)
            content += '\t}\n'

        for c in range(self.columns):
            content += '\t' + ' -- '.join(["m{}_{}".format(r + 1, c + 1) for r in range(self.rows)]) + '\n'

        content += '\n\t// Literals (bottom x-axis)\n'
        # content += '\tedge [style=invis];\n'
        # Literals
        for c in range(len(self.selectorlines)):
            v = '{}'.format(str(self.selectorlines[c]).replace("\\+", "¬"))
            style = 'color="#ffffff", fillcolor="#ffffff", style="filled,solid"'
            content += '\tm{}_{} [label="{}" {}];\n'.format(self.rows + 1, c + 1, v, style)
            content += '\tm{}_{} -- m{}_{};\n'.format(self.rows, c + 1, self.rows + 1, c + 1)

        for c in range(len(self.selectorlines), self.columns):
            style = 'color="#ffffff", fillcolor="#ffffff", style="filled,solid"'
            v = '—'
            content += '\tm{}_{} [label="{}" {}];\n'.format(self.rows + 1, c + 1, v, style)
            content += '\tm{}_{} -- m{}_{};\n'.format(self.rows, c + 1, self.rows + 1, c + 1)
        content += '\trank=same {' + ' '.join(
            ["m{}_{}".format(self.rows + 1, c + 1) for c in range(self.columns)]) + '}\n'

        # # Outputs
        # output_variables = dict()
        # for (o, (l, r)) in self.output_nanowires.items():
        #     if (l, r) in output_variables:
        #         output_variables[(l, r)].append(o)
        #     else:
        #         output_variables[(l, r)] = [o]
        # for ((l, r), os) in output_variables.items():
        #     if layer == l:
        #         for i in range(len(os)):
        #             v = os[i]
        #             style = 'color="#ffffff", fillcolor="#ffffff", style="filled,solid"'
        #             content += '\t m{}_{} [label="{}" {}];\n'.format(r, self.columns + 2, v, style)
        #         content += '\t m{}_{} -- m{}_{};\n'.format(r, self.columns + 1, r, self.columns + 2)
        # content += '\\draw (n%d_%d) -- (n%d_%d);\n' % (self.columns, self.rows - r, self.columns + 1, self.rows - r)

        content += '}'
        return content

    def get_functions(self):
        functions = []
        for (node, _) in self.wordlines:
            functions.append(node)
        return functions

    def __copy__(self):
        crossbar = SelectorCrossbar(self.rows, self.columns)
        for r in range(self.rows):
            for c in range(self.columns):
                crossbar.set_memristor(r, c, self.get_memristor(r, c).literal)
        crossbar.input_nanowires = self.input_nanowires.copy()
        crossbar.output_nanowires = self.output_nanowires.copy()
        return crossbar

    def instantiate(self, instance: Dict[str, bool]) -> SelectorCrossbar:
        crossbar = copy.deepcopy(self)

        for c in range(len(self.selectorlines)):
            literal = self.selectorlines[c]
            if literal == LITERAL("False", False):
                for r in range(crossbar.rows):
                    crossbar.set_memristor(r, c, LITERAL("False", False))
            elif literal == LITERAL("True", True):
                continue
            else:
                if not instance[literal.atom] and literal.positive:
                    for r in range(crossbar.rows):
                        crossbar.set_memristor(r, c, LITERAL("False", False))
                elif instance[literal.atom] and not literal.positive:
                    for r in range(crossbar.rows):
                        crossbar.set_memristor(r, c, LITERAL("False", False))
        return crossbar

    def eval(self, instance: Dict[str, bool], input_function: str = "1") -> Dict[str, bool]:
        crossbar_instance = self.instantiate(instance)
        graph = crossbar_instance.graph().copy()
        not_stuck_on_edges = [(u, v) for u, v, d in graph.edges(data=True) if
                              not (d['atom'] == 'True' and d['positive'])]
        graph.remove_edges_from(not_stuck_on_edges)

        evaluation = dict()
        for (output_variable, (output_layer, output_nanowire)) in self.output_nanowires.items():
            source = "L{}_{}".format(output_layer, output_nanowire)
            input_layer, input_nanowire = crossbar_instance.get_input_nanowire(input_function)
            sink = "L{}_{}".format(input_layer, input_nanowire)

            is_true = has_path(graph, source, sink)
            evaluation[output_variable] = is_true

        return evaluation
