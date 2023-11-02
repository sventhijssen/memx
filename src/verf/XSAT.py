from __future__ import annotations

import copy
import csv
import os
import time
from typing import List, Dict, Any, Tuple

import pexpect
from networkx import MultiGraph
from z3 import Bool

from utils import config
from utils.VerilogFix import VerilogFix
from core.BooleanFunctionCollection import BooleanFunctionCollection
from core.BooleanFunctionInterface import BooleanFunctionInterface
from core.benchmarks.Benchmark import VerilogBenchmark
from core.hardware.Crossbar import Crossbar, MemristorCrossbar
from core.expressions.BooleanExpression import LITERAL
from verf.EquivalenceChecker import EquivalenceChecker


class SubProblem:

    def __init__(self, subgraph: MultiGraph, literals: List[LITERAL]):
        self.subgraph = subgraph
        self.literals = literals


class XSAT(EquivalenceChecker):

    def __init__(self, crossbar: Crossbar, specification: BooleanFunctionInterface,
                 node_threshold: int = 250, depth_threshold: int = 5):
        super().__init__(crossbar, specification)
        config.log.add("Verification method: XSAT\n")
        self.node_threshold = node_threshold
        self.depth_threshold = depth_threshold

        self.xbar_filepath = config.abc_path.joinpath("xbar.v")
        self.spec_filepath = config.abc_path.joinpath("spec.v")
        self.sat_info_filepath = config.abc_path.joinpath("sat.csv")
        self.model_filepath = config.abc_path.joinpath("model.txt")

        if self.sat_info_filepath.exists():
            os.remove(self.sat_info_filepath)

        if self.model_filepath.exists():
            os.remove(self.model_filepath)

        self.divide_and_conquer_time = None
        self.start_time = None
        self.end_time = None
        self._crossbar_log = dict()
        self._iterations_log = []
        self._subproblems_log = []

        self.equivalent = None

    @staticmethod
    def _get_edge_properties(graph: MultiGraph) -> Dict[str, int]:
        memristor_stats = {"on": 0, "off": 0, "lit": 0}
        for _, _, _, edge_data in graph.edges(keys=True, data=True):
            atom = edge_data.get("atom")
            positive = edge_data.get("positive")
            literal = LITERAL(atom, positive)
            if literal == LITERAL("False", False):
                memristor_stats["off"] += 1
            elif literal == LITERAL("True", True):
                memristor_stats["on"] += 1
            else:
                memristor_stats["lit"] += 1
        return memristor_stats

    def _get_variable_count(self, xbar: MemristorCrossbar) -> Dict[str, int]:
        variable_count = dict()
        for r in range(xbar.rows):
            for c in range(xbar.columns):
                literal = xbar.get_memristor(r, c).literal
                if literal == LITERAL("False", False):
                    continue
                elif literal == LITERAL("True", True):
                    continue
                else:
                    atom = literal.atom
                    if atom not in variable_count:
                        variable_count[atom] = 0
                    variable_count[atom] += 1
        # We sort the variables in descending order in terms of their values (occurrences)
        variable_count = dict(sorted(variable_count.items(), key=lambda item: item[1], reverse=True))
        self._log_variable_count(variable_count)
        return variable_count

    @staticmethod
    def _graph_with_fixed_variable(graph: MultiGraph, literal: LITERAL) -> MultiGraph:
        graph = MultiGraph(copy.deepcopy(graph))
        for (u, v, k) in graph.edges:
            edge_data = graph.get_edge_data(u, v, k)
            e_atom = edge_data.get("atom")
            e_positive = edge_data.get("positive")
            if e_atom == literal.atom:
                if e_positive == literal.positive:
                    graph.edges[(u, v, k)]["atom"] = "True"
                    graph.edges[(u, v, k)]["positive"] = True
                else:
                    graph.edges[(u, v, k)]["atom"] = "False"
                    graph.edges[(u, v, k)]["positive"] = False
        return graph

    @staticmethod
    def _find_true_edge(graph: MultiGraph) -> Tuple[Any, Any, Any] | None:
        for (u, v, k) in graph.edges:
            edge_data = graph.get_edge_data(u, v, k)
            atom = edge_data.get("atom")
            positive = edge_data.get("positive")
            if LITERAL(atom, positive) == LITERAL("True", True):
                return u, v, k
        return None

    def _contract_graph(self, graph: MultiGraph) -> MultiGraph:
        graph = MultiGraph(graph.copy(as_view=False))

        # First, we remove all edges with FALSE as literal
        false_edges = set()
        for (u, v, k) in graph.edges:
            edge_data = graph.get_edge_data(u, v, k)
            atom = edge_data.get("atom")
            positive = edge_data.get("positive")
            if LITERAL(atom, positive) == LITERAL("False", False):
                false_edges.add((u, v, k))
        graph.remove_edges_from(false_edges)

        # Second, we contract all nodes that have TRUE as literal of an incident edge
        true_edge = self._find_true_edge(graph)
        while true_edge is not None:
            u, v, _ = true_edge
            victim = v  # This node will be removed
            victim_edges = graph.edges(victim, keys=True)
            # We remove all edges between u and v from the victim edges
            for x, y, k in victim_edges:

                # We ignore all edges that are between u and vas they will be removed by removing the victim node
                if u == x and v == y or u == y and v == x:
                    continue

                # This edge if between the victim and another node. Either x is the victim v, or y is the victim v.
                edge_data = graph.get_edge_data(x, y, k)
                if v == x:
                    l = 0
                    while (u, y, l) in graph.edges:
                        l += 1
                    graph.add_edge(u, y, l, **edge_data)
                else:
                    l = 0
                    while (u, x, l) in graph.edges:
                        l += 1
                    graph.add_edge(u, x, k, **edge_data)

            # We update the node data
            node_data = graph.nodes[victim]
            if "input_function" in node_data:
                graph.nodes[u]["input_function"] = node_data.get("input_function")
            if "output_functions" in node_data:
                if "output_functions" in graph.nodes[u]:
                    graph.nodes[u]["output_functions"].update(node_data.get("output_functions"))
                else:
                    graph.nodes[u]["output_functions"] = node_data.get("output_functions")

            # We remove the victim
            graph.remove_node(victim)

            true_edge = self._find_true_edge(graph)

        return graph

    def _log_iteration(self, step: str, graph: MultiGraph, total_time: float = None):
        iteration_log = dict()
        iteration_log["step"] = step
        iteration_log["graph"] = dict()
        iteration_log["graph"]["nodes"] = len(graph.nodes)
        iteration_log["graph"]["edges"] = self._get_edge_properties(graph)
        if total_time is not None:
            iteration_log["total_time"] = total_time
        self._iterations_log.append(iteration_log)

    def _divide_and_conquer(self, xbar: MemristorCrossbar) -> List[SubProblem]:
        variable_count = self._get_variable_count(xbar)

        variable_order = [(k, v) for k, v in variable_count.items()]

        graph = MultiGraph(xbar.graph())
        self._log_iteration("init", graph)

        print("\tStarted graph contraction")
        start_contract_time = time.time()
        graph = self._contract_graph(graph)
        end_contract_time = time.time()
        self._log_iteration("contract", graph, end_contract_time - start_contract_time)
        print("\tStopped graph contraction")

        final_subproblems = []

        subproblems = [SubProblem(graph, [])]
        while len(subproblems) != 0:
            subproblem = subproblems.pop(0)
            subgraph = subproblem.subgraph
            literals = subproblem.literals

            nodes = len(subgraph.nodes)

            # First, we check whether the graph has become smaller than the node threshold
            if self.node_threshold is None or nodes <= self.node_threshold:
                final_subproblems.append(subproblem)
                continue

            # Second, we look at the next variable and its count
            # We compare its count with the variable threshold
            variable, count = variable_order[len(literals)]

            if len(subproblem.literals) >= self.depth_threshold:
                final_subproblems.append(subproblem)
                continue

            positive_literal = LITERAL(variable, True)
            negative_literal = LITERAL(variable, False)

            print("\tStarted fixating variable")
            start_fixate_time = time.time()
            positive_subgraph = self._graph_with_fixed_variable(subgraph, positive_literal)
            end_fixate_time = time.time()
            self._log_iteration("fix", positive_subgraph, end_fixate_time - start_fixate_time)
            start_fixate_time = time.time()
            negative_subgraph = self._graph_with_fixed_variable(subgraph, negative_literal)
            end_fixate_time = time.time()
            self._log_iteration("fix", negative_subgraph, end_fixate_time - start_fixate_time)
            print("\tStopped fixating variable")

            print("\tStarted graph contraction")
            start_contract_time = time.time()
            positive_subgraph = self._contract_graph(positive_subgraph)
            end_contract_time = time.time()
            self._log_iteration("contract", positive_subgraph, end_contract_time - start_contract_time)
            start_contract_time = time.time()
            negative_subgraph = self._contract_graph(negative_subgraph)
            end_contract_time = time.time()
            self._log_iteration("contract", negative_subgraph, end_contract_time - start_contract_time)
            print("\tStopped graph contraction")

            subproblems.append(SubProblem(positive_subgraph, literals + [positive_literal]))
            subproblems.append(SubProblem(negative_subgraph, literals + [negative_literal]))

        return final_subproblems

    def _write_graph(self, subproblem: SubProblem):
        input_variables_str = ", ".join(list(self.specification.get_input_variables()))
        output_variables_str = ", ".join(list(self.specification.get_output_variables()))

        subgraph = subproblem.subgraph

        T = len(subgraph.nodes)

        content = ""
        content += "module test (\n"
        content += "\t{} );\n".format(input_variables_str)
        content += "\tinput {};\n".format(input_variables_str)
        content += "\toutput {};\n".format(output_variables_str)

        wires = []
        for v in subgraph.nodes:
            for t in range(0, T):
                wires.append("{}_{}".format(v, t))
        content += "\twire {};\n".format(", ".join(wires))

        # Input nanowires
        input_wire_nodes = set()
        for v, node_data in subgraph.nodes(data=True):
            if "input_function" in node_data:
                input_wire_nodes.add(v)
                for t in range(T):
                    content += "\tassign {}_{} = 1'b1;\n".format(v, t)

        # Time step t > 0
        for v in subgraph.nodes:
            if v in input_wire_nodes:
                continue

            for t in range(1, T):
                conjunctions = []
                for u in subgraph.neighbors(v):
                    subdisjunction = []
                    for (x, y, k) in subgraph.edges(v, keys=True):
                        if x == v and y == u:
                            edge_data = subgraph.get_edge_data(u, v, k)
                            atom = edge_data.get("atom")
                            positive = edge_data.get("positive")
                            literal = LITERAL(atom, positive)
                            subdisjunction.append(str(literal))
                    conjunctions.append("({}) & {}_{}".format(" | ".join(subdisjunction), u, t - 1))

                if len(conjunctions) == 0:
                    continue

                content += "\tassign {}_{} = {};\n".format(v, t, " | ".join(conjunctions))

        q = dict()
        # Output nanowires
        for v, node_data in subgraph.nodes(data=True):
            if "output_functions" in node_data:
                output_variables = node_data.get("output_functions")
                for output_variable in output_variables:
                    if output_variable not in q:
                        q[output_variable] = []
                    q[output_variable].append("(({}))".format(" | ".join(["{}_{}".format(v, t) for t in range(0, T)])))

        for k, v in q.items():
            content += "\tassign {} = {};\n".format(k, " | ".join(v))
        content += "endmodule"

        with open(self.xbar_filepath, 'w') as f:
            f.write(content)

    def _log_crossbar(self, xbar: MemristorCrossbar):
        R = xbar.rows
        C = xbar.columns
        self._crossbar_log["rows"] = R
        self._crossbar_log["columns"] = C
        self._crossbar_log["time_steps"] = 2 * min(R - 1, C) + 1

    def _log_variable_count(self, variable_count: Dict[str, int]):
        self._crossbar_log["variable_count"] = variable_count

    def _log_subproblem(self, subproblem_log: Dict[str, Any], subproblem: SubProblem):
        subproblem_log["graph"] = dict()
        subproblem_log["graph"]["nodes"] = len(subproblem.subgraph.nodes)
        subproblem_log["graph"]["edges"] = self._get_edge_properties(subproblem.subgraph)
        subproblem_log["fixed_literals"] = list(map(lambda lit: str(lit), subproblem.literals))
        subproblem_log["time_steps"] = len(subproblem.subgraph.nodes)

    def _log_sat(self, subproblem_log: Dict[str, Any]):
        subproblem_log["sat"] = dict()

        time.sleep(3)

        if not self.sat_info_filepath.exists():
            return

        with open(self.sat_info_filepath, 'r') as f:
            csv_file = csv.reader(f, delimiter='\t')

            i = 0
            for line in csv_file:
                if i == 0:
                    subproblem_log["sat"]["clauses"] = int(line[1])
                    subproblem_log["sat"]["literals"] = int(line[2])
                    break

    def _write_specification(self, specification: BooleanFunctionCollection, subproblem: SubProblem):
        literals = subproblem.literals

        for boolean_function in specification.boolean_functions:
            verilog_benchmark = boolean_function.to_verilog()

            verilog_fix = VerilogFix(verilog_benchmark, self.spec_filepath)
            verilog_fix.fix(literals)

            # TODO: The code below contains a bug somewhere. Hence, we use VerilogFix. However, in the future,
            #  we would want to use the method fix(). verilog = verilog_benchmark.verilog
            #
            # new_functions = dict()
            # for output_function, formula in verilog.functions.items():
            #     expression = formula.verilog.boolean_expression
            #     for literal in literals:
            #         expression = expression.fix(literal.atom, literal.positive)
            #     new_verilog_formula = VerilogFormula()
            #     new_verilog_formula.output = output_function
            #     new_verilog_formula.boolean_expression = expression
            #     new_formula = Formula(new_verilog_formula)
            #     new_functions[output_function] = new_formula
            #
            # verilog.functions = new_functions
            # subspec = VerilogBenchmark(verilog)
            # subspec.write(self.spec_filepath)

    def is_equivalent(self, sampling_size: int = 0) -> bool:
        print("XSAT started")
        self.start_time = time.time()

        assert isinstance(self.specification, BooleanFunctionCollection)
        for boolean_function in self.specification.boolean_functions:
            assert isinstance(boolean_function, VerilogBenchmark)
        assert isinstance(self.boolean_function, MemristorCrossbar)

        xbar = self.boolean_function
        self._log_crossbar(xbar)

        start_divide_and_conquer_time = time.time()
        subproblems = self._divide_and_conquer(xbar)
        end_divide_and_conquer_time = time.time()
        self.divide_and_conquer_time = end_divide_and_conquer_time - start_divide_and_conquer_time

        for subproblem in subproblems:
            print("\tSubproblem with fixed literals: {}".format(subproblem.literals))

            if self.sat_info_filepath.exists():
                os.remove(self.sat_info_filepath)

            subproblem_log = dict()
            self._log_subproblem(subproblem_log, subproblem)

            sub_specification = copy.deepcopy(self.specification)

            start_write_time = time.time()
            self._write_specification(sub_specification, subproblem)
            self._write_graph(subproblem)
            end_write_time = time.time()
            subproblem_log["write_time"] = end_write_time - start_write_time

            # Based on https://stackoverflow.com/questions/20061176/python-wait-and-check-if-file-is-created-completely-by-external-program
            while True:
                try:
                    with open(self.xbar_filepath, 'rb') as _:
                        pass
                    with open(self.spec_filepath, 'rb') as _:
                        break
                except IOError:
                    time.sleep(3)

            print("\tCrossbar and specification written to file.")

            start_cec_time = time.time()
            # Start a process for the ABC tool
            process = pexpect.spawn(config.abc_cmd, cwd=str(config.abc_path), timeout=14400)
            process.sendline("cec {} {};".format(self.spec_filepath.name, self.xbar_filepath.name))
            index = process.expect(['.*Networks are equivalent.*', '.*Networks are NOT EQUIVALENT.*'])
            end_cec_time = time.time()
            self._log_sat(subproblem_log)
            subproblem_log["cec_time"] = end_cec_time - start_cec_time

            self.equivalent = index == 0

            self._subproblems_log.append(subproblem_log)

            if not self.equivalent:
                self.end_time = time.time()
                config.log.add_json(self.get_log())
                print("NOT equivalent")
                return self.equivalent

        self.end_time = time.time()
        config.log.add_json(self.get_log())
        print("Equivalent")

        print("XSAT stopped")
        return self.equivalent

    def to_formula(self, output_variable: str) -> Bool:
        raise NotImplementedError()

    def get_log(self) -> Dict[str, Any]:
        return {
            "type": self.__class__.__name__,
            "depth_threshold": self.depth_threshold,
            "node_threshold": self.node_threshold,
            "crossbar": self._crossbar_log,
            "total_divide_and_conquer_time": self.divide_and_conquer_time,
            "iterations": self._iterations_log,
            "subproblems": self._subproblems_log,
            "equivalent": self.equivalent,
            "total_time": self.end_time - self.start_time
        }
