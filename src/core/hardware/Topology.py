from __future__ import annotations

import re
from pathlib import Path
from typing import Dict, Set

from networkx import MultiDiGraph, topological_sort, dag_longest_path

from utils.Parser import Parser
from core.BooleanFunction import BooleanFunction
from core.hardware.Crossbar import Crossbar

from core.hardware.Component import Component


class TopologyParser(Parser):
    """
    A class to parse a topology from a TOPO file.
    """

    def __init__(self, content: str):
        """
        Given the topology file, w
        :param file_path:
        """
        super().__init__()
        self.content = content
        self.topology = None

    def parse(self) -> Topology:

        graph = MultiDiGraph()

        xbar_start_lines = []
        lines = self.content.splitlines(keepends=True)
        for i in range(len(lines)):
            line = lines[i]
            if line.startswith(".xbar"):
                xbar_start_lines.append(i)

        for i in xbar_start_lines:
            xbar_model_start = 0
            xbar_model_end = 0

            for j in range(i, -1, -1):
                line = lines[j]
                if line.startswith(".model"):
                    xbar_model_start = j
                    break
            for j in range(i + 1, len(lines), 1):
                line = lines[j]
                if line.startswith(".end"):
                    xbar_model_end = j
                    break

            sub_content = "".join(lines[xbar_model_start:xbar_model_end])

            xbar = Crossbar.from_string(sub_content)

            graph.add_node(xbar)

        topology = Topology(graph)

        return topology


class Topology(Component):
    """
    Class to represent a topology.
    """

    def __init__(self, graph: MultiDiGraph, file_path: Path = None, name: str = None):
        """
        A topology is constructed from the given multi-digraph. This entails that multiple directed edges may exist
        between nodes. A node is another type of hardware, such as a crossbar or a staircase.
        :param graph: A
        :param file_path:
        :param name:
        """
        super().__init__(name)
        self.file_path = file_path
        self.graph = graph

    @staticmethod
    def get_file_extension() -> str:
        return "topo"

    def get_input_variables(self) -> Set[str]:
        input_variables = set()
        for node in self.graph.nodes:
            input_variables.update(node.get_input_variables())
        return input_variables

    def get_output_variables(self) -> Set[str]:
        output_variables = set()
        for node in self.graph.nodes:
            output_variables.update(node.get_output_variables())
        return output_variables

    def get_auxiliary_variables(self) -> Set[str]:
        auxiliary_variables = set()
        for node in self.graph.nodes:
            auxiliary_variables.update(node.auxiliary_variables())
        return auxiliary_variables

    @staticmethod
    def read(filepath: Path) -> BooleanFunction:
        with open(filepath, 'r') as f:
            content = f.read()
        return Topology.from_string(content)

    @staticmethod
    def from_string(content: str) -> BooleanFunction:
        topology_parser = TopologyParser(content)
        topology = topology_parser.parse()
        return topology

    def to_string(self) -> str:
        content = ""
        content += ".model {}\n".format(self.get_name())
        content += ".inputs {}\n".format(' '.join(self.get_input_variables()))
        content += ".outputs {}\n".format(' '.join(self.get_output_variables()))
        content += ".topo\n"
        for node in self.graph.nodes:
            assert isinstance(node, Crossbar)
            content += node.to_string()
        content += ".end\n"
        return content

    def to_json(self) -> Dict:
        return {
            "type": "topology",
            "name": self.get_name(),
            "graph":
                {
                    "nodes": list(map(lambda v: v.to_json(), self.graph.nodes)),
                    "edges": list(map(lambda e: (e[0].get_name(), e[1].get_name()), self.graph.edges))
                }
        }

    def to_dot(self) -> str:
        content = ""
        content += 'graph {} {{\n'.format(self.get_name())
        content += '\trankdir=TB;\n'
        content += '\tcompound=true;\n'
        content += '\tgraph [nodesep="0.2", ranksep="0.2"];\n'
        content += '\tcharset="UTF-8";\n'
        content += '\tratio=fill;\n'
        content += '\tsplines=ortho;\n'
        content += '\toverlap=scale;\n'
        content += '\tnode [shape=circle, fixedsize=true, width=0.4, fontsize=4];\n'
        content += '\n'

        node_to_nr = dict()
        for node in topological_sort(self.graph):
            for sub_content in node.draw():
                i = node.get_name()
                node_to_nr[node] = i
                import re
                subgraph = re.sub(r'(m\d+)', r's{}\1'.format(i), sub_content)
                subgraph = subgraph.splitlines()
                subgraph = subgraph[1:-1]
                subgraph = "\n".join(subgraph)
                content += '\tsubgraph cluster{} {{\n'.format(i)
                content += '\t\tlabel="{}"\n'.format(i)
                content += subgraph
                content += '\n\t}\n\n'

        # TODO: Change isinstance(x0, CLASS) <-> ugly
        for (node0, node1, ei) in self.graph.edges:
            if isinstance(node0, Crossbar):
                edge_data = self.graph.get_edge_data(node0, node1, ei)
                x0 = node0
                x1 = node1
                l0 = edge_data.get("l0")
                i0 = edge_data.get("i0")
                l1 = edge_data.get("l1")
                i1 = edge_data.get("i1")
                nr0 = node_to_nr.get(x0)
                nr1 = node_to_nr.get(x1)

                if l0 == 0:  # Row
                    r0 = i0 + 1
                    c0 = x0.columns
                else:  # Column
                    r0 = x0.rows + 1
                    c0 = i0 + 1

                if l1 == 0:  # Row
                    r1 = i1 + 1
                    c1 = 0
                else:  # Column
                    r1 = x1.rows + 1
                    c1 = i1 + 1

                content += '\ts{}m{}_{}:e -- s{}m{}_{}:s [style = dashed, penwidth = 1, color="#000000", splines=ortho, constraint=false];\n'.format(nr0, r0, c0, nr1, r1, c1)
            else:
                edge_data = self.graph.get_edge_data(node0, node1, ei)
                s0 = node0
                s1 = node1
                x0 = s0.get_crossbars()[-1]
                x1 = s1.get_crossbars()[0]
                l0 = edge_data.get("l0")
                i0 = edge_data.get("i0")
                l1 = edge_data.get("l1")
                i1 = edge_data.get("i1")
                nr0 = node_to_nr.get(x0)
                nr1 = node_to_nr.get(x1)

                if l0 == 0:  # Row
                    r0 = i0 + 1
                    c0 = x0.columns
                else:  # Column
                    r0 = x0.rows + 1
                    c0 = i0 + 1

                if l1 == 0:  # Row
                    r1 = i1 + 1
                    c1 = 0
                else:  # Column
                    r1 = x1.rows + 1
                    c1 = i1 + 1

                content += '\ts{}m{}_{}:e -- s{}m{}_{}:s [style = dashed, penwidth = 1, color="#000000", splines=ortho, constraint=false];\n'.format(nr0, r0, c0, nr1, r1, c1)
        content += '}'
        return content

    def get_log(self) -> Dict:
        return {
            "id": id(self),
            "type": self.__class__.__name__,
            "nodes": len(self.graph.nodes),
            "inter_connections": len(self.graph.edges),
            "critical_path_length": len(dag_longest_path(self.graph))
        }

    # def get_log(self) -> Dict:
    #     return {
    #         "id": id(self),
    #         "type": self.__class__.__name__,
    #         "nodes": list(map(lambda node: node.get_log(), self.bipartite_graph.nodes)),
    #         "function_wires": list(map(lambda edge: (id(edge[0]), id(edge[1])), self.bipartite_graph.edges))
    #     }

    def eval(self, instance: Dict[str, bool], input_function: str = "1") -> Dict[str, bool]:
        evaluations = {input_function: True}
        evaluations.update(instance)

        i = 0
        for node in topological_sort(self.graph):
            for input_function in node.get_input_nanowires().keys():
                if evaluations.get(input_function):
                    evaluation = node.eval(evaluations, input_function)
                    for key, value in evaluation.items():
                        if key in evaluations:
                            current_value = evaluations.get(key)
                            if not current_value:
                                evaluations[key] = value
                        else:
                            evaluations[key] = value
            i += 1
        return evaluations
