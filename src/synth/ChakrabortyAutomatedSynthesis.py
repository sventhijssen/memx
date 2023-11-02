import time
from datetime import datetime
from typing import Any, Dict

from utils import config
from core.decision_diagrams.BDD import BDD
from synth.SynthesisMethod import SynthesisMethod
from core.expressions.BooleanExpression import LITERAL
from core.hardware.Crossbar import MemristorCrossbar


class ChakrabortyAutomatedSynthesis(SynthesisMethod):

    def __init__(self, bdd: BDD):
        """
        This synthesis method is based on the work by D. Chakraborty et al. [1].

        [1] Chakraborty, D., & Jha, S. K. (2017, March).
        Automated synthesis of compact crossbars for sneak-path based in-memory computing.
        In Design, Automation & Test in Europe Conference & Exhibition (DATE), 2017 (pp. 770-775). IEEE.
        """
        super(ChakrabortyAutomatedSynthesis, self).__init__(bdd)

    def map(self) -> MemristorCrossbar:
        print("Chakraborty's mapping method started")
        print(datetime.now())

        self.start_time = time.time()

        rows = len(self.dd.dag.nodes)
        columns = len(self.dd.dag.edges)

        crossbar = MemristorCrossbar(rows, columns)

        # We assign each node to a layer with the terminal node to the bottom-most nanowire
        # and the root node to the top-most nanowire
        r = 0
        input_variables = set()
        input_nodes = dict()
        root_nodes = dict()
        node_layers = dict()
        for (current_node, node_data) in self.dd.dag.nodes(data=True):
            input_variables.add(node_data["variable"])
            if node_data["root"]:
                output_variables = node_data["output_variables"]
                for output_variable in output_variables:
                    root_nodes[output_variable] = (0, r)
            if node_data["terminal"]:
                input_variable = node_data["variable"]
                input_nodes[input_variable] = (0, r)
            node_layers[current_node] = r
            r += 1

        c = 0
        for (current_node, node_data) in self.dd.dag.nodes(data=True):
            out_edges = self.dd.dag.edges(current_node, data=True)
            variable = node_data['variable']

            positive_child_node = None
            negative_child_node = None
            for (_, child_node, edge_data) in out_edges:
                literal = edge_data.get("literal")
                if literal.positive:
                    positive_child_node = child_node
                else:
                    negative_child_node = child_node

            if positive_child_node is not None:
                r_current_node = node_layers[current_node]
                r_child_node = node_layers[positive_child_node]
                crossbar.set_memristor(r_current_node, c, LITERAL(variable, True))
                crossbar.set_memristor(r_child_node, c, LITERAL("True", True))
                c += 1
            if negative_child_node is not None:
                r_current_node = node_layers[current_node]
                r_child_node = node_layers[negative_child_node]
                crossbar.set_memristor(r_current_node, c, LITERAL(variable, False))
                crossbar.set_memristor(r_child_node, c, LITERAL("True", True))
                c += 1

        crossbar.input_variables = list(input_variables)
        for (input_function, (layer, nanowire)) in input_nodes.items():
            crossbar.set_input_nanowire(input_function, nanowire, layer=layer)
        for (output_function, (layer, nanowire)) in root_nodes.items():
            crossbar.set_output_nanowire(output_function, nanowire, layer=layer)

        self.end_time = time.time()

        self.component = crossbar

        config.log.add_json(self.get_log())

        print("Chakraborty's mapping method stopped")

        return crossbar

    def get_log(self) -> Dict[str, Any]:
        return {
            "synthesis_method": self.__class__.__name__,
            "nodes": len(self.dd.dag.nodes),
            "edges": len(self.dd.dag.edges),
            "rows": self.component.get_rows(),
            "columns": self.component.get_columns(),
            "synthesis_time": self.end_time - self.start_time
        }
