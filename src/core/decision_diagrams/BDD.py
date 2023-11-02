from __future__ import annotations

import copy
from pathlib import Path
from typing import Dict, List, Set, Any

from networkx import DiGraph, topological_sort, has_path

from utils import config
from utils.BDDParser import BDDParser
from core.decision_diagrams.DD import DD


class BDD(DD):
    """
    A class to represent a binary decision diagram (BDD).
    A BDD can either be a ROBDD or SBDD, and is defined by its directed acyclic graph (DAG).
    """

    TRUE = "1"
    FALSE = "0"

    def __init__(self, graph: DiGraph, variable_order: List[str], name: str = None):
        """
        A BDD is constructed from the given graph.
        :param graph: 
        """
        super().__init__(graph, name)
        self.variable_order = variable_order
        self.positive_terminal_node = None
        self.negative_terminal_node = None
        self._set_root_and_terminal_nodes()
        config.log.add_json(self.get_log())

    @staticmethod
    def get_file_extension() -> str:
        return "bdd"

    def get_log(self) -> List[Dict[str, Any]] | Dict[str, Any]:
        return {
            "name": self.get_name(),
            "nodes": len(self.dag.nodes),
            "edges": len(self.dag.edges),
            "roots": len(self.root_nodes),
            "positive_terminal_node": self.positive_terminal_node is not None,
            "negative_terminal_node": self.negative_terminal_node is not None
        }

    def get_input_variables(self) -> Set[str]:
        """
        Returns the input variables from this BDD.
        :return: A set of the input variables of this BDD.
        """
        input_variables = set()
        for node, node_data in self.dag.nodes(data=True):
            variable = node_data["variable"]
            if variable != self.FALSE and variable != self.TRUE:
                input_variables.add(variable)
        return input_variables

    def get_output_variables(self) -> Set[str]:
        """
        Returns the output variables from this BDD.
        :return: A set of the output variables of this BDD.
        """
        output_variables = set()
        for node, node_data in self.dag.nodes(data=True):
            if "output_variables" in node_data:
                output_variables.update(node_data["output_variables"])
        return output_variables

    def get_auxiliary_variables(self) -> Set[str]:
        return set()

    def _set_root_and_terminal_nodes(self):
        for node, node_data in self.dag.nodes(data=True):
            variable = node_data.get("variable")
            root = node_data.get("root")
            if root:
                self.root_nodes.add(node)

            if variable == self.FALSE:
                self.negative_terminal_node = node
            elif variable == self.TRUE:
                self.positive_terminal_node = node

    @staticmethod
    def read(file_path: Path) -> BDD:
        bdd_parser = BDDParser(file_path)
        bdd_module = bdd_parser.bdd_module
        return BDD(bdd_module.dag, bdd_module.variable_order, bdd_module.module_name)

    def to_string(self) -> str:
        """
        Returns a BDD description of this BDD.
        :return: A BDD description of this BDD.
        """
        content = ""
        content += ".model {}\n".format(self.get_name())
        content += ".inputs {}\n".format(" ".join(self.get_input_variables()))
        content += ".outputs {}\n".format(" ".join(self.get_output_variables()))
        content += ".order {}\n".format(" ".join(self.variable_order))
        content += ".bdd\n"
        for (node, node_data) in self.dag.nodes(data=True):
            successors = self.dag.successors(node)
            positive_child = -1
            negative_child = -1
            for successor in successors:
                edge_data = self.dag.get_edge_data(node, successor)
                literal = edge_data.get("literal")
                if literal.positive:
                    positive_child = successor
                else:
                    negative_child = successor
            if node_data["root"]:
                output_variables = " ".join(node_data["output_variables"])
                content += "{} {} {} {} {}\n".format(node, positive_child, negative_child, node_data["variable"],
                                                     output_variables)
            else:
                content += "{} {} {} {}\n".format(node, positive_child, negative_child, node_data["variable"])
        content += ".end\n"
        return content

    @staticmethod
    def from_string(content) -> BDD:
        bdd_module = BDDParser.from_string(content)
        return BDD(bdd_module.dag, bdd_module.variable_order, bdd_module.module_name)

    def get_variable_order(self) -> List[str]:
        """
        Returns the variable order of the input variables of this BDD.
        :return: A list of the input variables such that they are in variable order.
        """
        return self.variable_order

    def to_dot(self) -> str:
        """
        Returns a DOT description for this BDD similar to the DOT description produced by ABC.
        :return: A DOT description for this BDD.
        """
        layers = self.get_variable_order()
        output_variables = list(self.get_output_variables())
        content = "digraph \"DD\" {\n"
        content += "size = \"7.5,10\"\n"
        content += "center = true;\n"
        content += "edge [dir = none];\n"
        content += "{ node [ shape = plaintext];\n"
        content += "  edge [style = invis];\n"
        content += "  \"CONST NODES\" [style = invis];\n"
        for layer in layers:
            content += "\" {} \" -> ".format(layer)
        content += "\"CONST NODES\";\n"
        content += "}\n"
        content += "{ rank = same; node [shape = box]; edge [style = invis];\n"
        for i in range(len(output_variables)):
            output_variable = output_variables[i]
            content += "\"  {0}  \"".format(output_variable)
            if i < len(output_variables) - 1:
                content += " -> "
        content += "; }\n"
        is_new_variable = True
        for node in topological_sort(self.dag):
            node_data = self.dag.nodes[node]
            variable = node_data["variable"]
            if variable == self.FALSE or variable == self.TRUE:
                continue
            if is_new_variable:
                content += "{{ rank = same; \" {0} \";\n".format(variable)
            content += "\"{}\"\n".format(node)
            content += "}\n"
        content += "{ rank = same; \"CONST NODES\";\n"
        content += "{ node [shape = box];\n"

        if self.negative_terminal_node is not None:
            content += "\"{0}\";\n".format(self.negative_terminal_node)
        if self.positive_terminal_node is not None:
            content += "\"{0}\";\n".format(self.positive_terminal_node)
        content += "}\n"
        content += "}\n"
        for root_node in self.root_nodes:
            for output_variable in self.dag.nodes[root_node]["output_variables"]:
                content += "\"  {}  \" -> \"{}\" [style = solid];\n".format(output_variable, root_node)
        for u, v in self.dag.edges:
            edge_data = self.dag.get_edge_data(u, v)
            literal = edge_data.get("literal")
            if literal.positive:
                content += "\"{}\" -> \"{}\";\n".format(u, v)
            else:
                content += "\"{}\" -> \"{}\" [style = dashed];\n".format(u, v)

        if self.negative_terminal_node is not None:
            content += "\"{0}\" [label = \"0\"];\n".format(self.negative_terminal_node)
        if self.positive_terminal_node is not None:
            content += "\"{0}\" [label = \"1\"];\n".format(self.positive_terminal_node)

        content += "}\n"
        return content

    def eval(self, instance: Dict[str, bool]) -> Dict[str, bool]:
        """
        Evaluates this BDD by traversing the DAG from root nodes to leaf nodes (positive and/or negative terminal node).
        :param instance: A dictionary mapping the input variables to a Boolean truth value (true/false).
        :return: A dictionary mapping the output variables to a Boolean truth value (true/false).
        """

        # First, we instantiate the BDD. This means that we remove edges from the BDD that evaluate to False such that
        # only edges remain where the literal evaluates to the given truth value.
        dag = copy.deepcopy(self.dag)  # self.dag.copy(as_view=False)
        false_edges = set()
        for (u, v) in dag.edges:
            edge_data = dag.get_edge_data(u, v)
            literal = edge_data.get("literal")
            evaluation = literal.eval(instance)
            if not evaluation:
                false_edges.add((u, v))
        dag.remove_edges_from(false_edges)

        # Now, we try to find a path from root node to leaf node.
        evaluations = dict()
        for root_node in self.root_nodes:
            true_path = False
            false_path = False
            if self.positive_terminal_node is not None:
                if has_path(dag, root_node, self.positive_terminal_node):
                    true_path = True
            if self.negative_terminal_node is not None:
                if has_path(dag, root_node, self.negative_terminal_node):
                    false_path = True

            # There must exactly be one path between the root node and either the positive or
            # the negative terminal node.
            if true_path == false_path:
                raise Exception("There must be either a path from the root node to the positive terminal node or a "
                                "path from the root node to the negative terminal node.")

            # Converts the root node into the output variables
            output_variables = dag.nodes[root_node]["output_variables"]
            for output_variable in output_variables:
                evaluations[output_variable] = true_path

        return evaluations

    def prune(self) -> BDD:
        """
        Prunes this BDD. Pruning entails the removal of the negative terminal node.
        :return: A BDD without the negative terminal node of this BDD.
        """
        dag = self.dag.copy(as_view=False)
        if self.negative_terminal_node is not None:
            dag.remove_node(self.negative_terminal_node)
        return BDD(dag, self.variable_order, self.name)
