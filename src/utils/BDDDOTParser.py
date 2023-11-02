from __future__ import annotations

import itertools
import os
import re
import shutil
import time
from typing import Set, Dict, Any, List

import pexpect
from networkx import DiGraph, set_node_attributes
from pexpect import EOF, TIMEOUT

from utils import config
from utils.DDParser import DDParser
from core.benchmarks import Benchmark
from core.decision_diagrams.BDD import BDD
from core.decision_diagrams.BDDCollection import BDDCollection
from core.expressions.BooleanExpression import LITERAL


class BDDDOTParser(DDParser):
    """
    A class to parse a BDD from a DOT file. The DOT file is constructed using ABC.
    """

    def __init__(self, benchmark: Benchmark, multi_output: bool = True):
        """
        Constructs either a single Shared Binary Decision Diagram (SBDD) or a set of
        Reduced Ordered Binary Decision Diagrams (ROBDDs) from the given benchmark.
        An SBDD is constructed when the given parameter multi_output is True, otherwise a set of ROBDDs is constructed.
        :param benchmark: The given benchmark.
        :param multi_output: If true, then a single SBDD is constructed. Otherwise, a set of ROBDDs is constructed.
        """
        super().__init__(benchmark)
        self.multi_output = multi_output
        if self.multi_output:
            self._bdd_type = "SBDD"
            self.dot_file = config.abc_path.joinpath(self.benchmark.name + ".dot")
        else:
            self._bdd_type = "ROBDD"
            self.dot_file = config.abc_path.joinpath("copy.dot")
        self.abc_file_path = config.abc_path.joinpath(self.benchmark.file_path.name)

    def get_log(self) -> List[Dict[str, Any]] | Dict[str, Any]:
        return {
            "bdds": [bdd.get_log() for bdd in self.dd_collection]
        }

    @staticmethod
    def _parse_dot(dot: str, name: str = None) -> BDD:
        """
        Converts the DOT content to a BDD.
        :param dot: The DOT content generated using ABC.
        :return: A BDD.
        """
        dag = DiGraph()

        # Get the names of the nodes and the values on which they are mapped
        raw_layers = list(re.findall(r'{\s*rank\s*=\s*same;([^}]+);\n}', dot))

        layers = []
        for raw_layer in raw_layers:
            layers.append(raw_layer.replace(' ', '').replace('\n', '').replace('"', '').split(';'))

        # Remove function output
        layers = layers[:-1]

        # Strip the 'rank' and 'node' objects
        stripped_content = re.sub(r'{\s(?:rank|node)[^}]+}', '', dot)

        node_variable = dict()

        raw_output_variable_nodes = re.findall(r'"\s*([\w\d\[\]]+)\s*"\s->\s"([\w\d]+)"\s\[style\s=\ssolid\]',
                                               stripped_content)
        raw_output_variable_nodes = [(i[1], i[0]) for i in raw_output_variable_nodes]
        output_variable_nodes = dict()
        for raw_output_variable_node in raw_output_variable_nodes:
            node = raw_output_variable_node[0]
            output_variable = raw_output_variable_node[1]
            if node not in output_variable_nodes:
                output_variable_nodes[node] = set()
            output_variable_nodes[node].add(output_variable)

        # Find all edges defined by NODE -> NODE with optional [STYLE] parameter and
        # leave nodes, defined by NODE [LABEL]
        raw_edges = re.findall(
            r'"([\w\d\s\[\]]+)"\s->\s"([\w\d\s]+)"(?:\s\[style\s=\s(solid|dashed)\])?|"([\w\d\s]+)"\s\[label\s=\s"(\d)"\]',
            stripped_content)

        variable_order = [x[0] for x in layers]
        # Build BDD (directed graph) by adding the nodes
        for i in range(len(layers)):
            layer = layers[i]
            input_variable = layer[0]
            nodes = layer[1:]
            for node in nodes:
                node_variable[node] = layer[0]
                if node in output_variable_nodes:
                    dag.add_node(node, output_variables=output_variable_nodes.get(node), variable=input_variable, terminal=False, root=True)
                else:
                    dag.add_node(node, output_variables=set(), variable=input_variable, terminal=False, root=False)

        has_terminal_zero = list(filter(lambda tup: tup[4] == '0', raw_edges))
        has_terminal_one = list(filter(lambda tup: tup[4] == '1', raw_edges))

        # Normal BDD
        if len(has_terminal_one) > 0 and len(has_terminal_zero) > 0:
            terminal_one = list(map(lambda tup: list(tup)[3], filter(lambda tup: tup[4] == '1', raw_edges)))[0]
            terminal_zero = list(map(lambda tup: list(tup)[3], filter(lambda tup: tup[4] == '0', raw_edges)))[0]

            dag.add_node(terminal_one, variable='1', terminal=True, root=False)
            dag.add_node(terminal_zero, variable='0', terminal=True, root=False)

            output_variables = list(itertools.chain(*output_variable_nodes.values()))

            formatted_output_variables = ['  {}  '.format(output_variable) for output_variable in output_variables]

            # Add the edges of the graph
            for raw_edge in raw_edges:
                if raw_edge[0] != '' and raw_edge[0] not in formatted_output_variables:
                    variable = node_variable[raw_edge[0]]
                    if raw_edge[2] != 'dashed':
                        dag.add_edge(raw_edge[0], raw_edge[1], literal=LITERAL(variable, True))
                    else:
                        dag.add_edge(raw_edge[0], raw_edge[1], literal=LITERAL(variable, False))

            # We set the output variables for the terminal nodes
            if terminal_one in output_variable_nodes:
                output_variables = output_variable_nodes[terminal_one]
                set_node_attributes(dag, {terminal_one: output_variables}, "output_variables")
                set_node_attributes(dag, {terminal_one: True}, "root")
            if terminal_zero in output_variable_nodes:
                output_variables = output_variable_nodes[terminal_zero]
                set_node_attributes(dag, {terminal_zero: output_variables}, "output_variables")
                set_node_attributes(dag, {terminal_zero: True}, "root")

        # Has positive terminal, but does not negative terminal: always true
        elif len(has_terminal_one) > 0 and len(has_terminal_zero) == 0:
            terminal_one = list(map(lambda tup: list(tup)[3], filter(lambda tup: tup[4] == '1', raw_edges)))[0]
            output_variables = output_variable_nodes[terminal_one]
            # dag.add_node('0', variable='0', terminal=True, root=True)
            dag.add_node(terminal_one, variable='1', terminal=True, root=True, output_variables=output_variables)

        # Does not have positive terminal, but has negative terminal: always false
        elif len(has_terminal_one) == 0 and len(has_terminal_zero) > 0:
            terminal_zero = list(map(lambda tup: list(tup)[3], filter(lambda tup: tup[4] == '0', raw_edges)))[0]
            output_variables = output_variable_nodes[terminal_zero]
            # dag.add_node('1', variable='1', terminal=True, root=False)
            dag.add_node(terminal_zero, variable='0', terminal=True, root=True, output_variables=output_variables)
        else:
            Exception("BDD must at least have a positive or a negative terminal.")

        bdd = BDD(dag, variable_order, name)
        # config.log.add_json(bdd.get_log())
        return bdd

    def _write_dot(self) -> Dict[str, str]:
        """
        Writes the DOT content using the ABC tool.
        :return: Returns a set of DOT contents. A single DOT content for an SBDD, and one or more for ROBDDs.
        """
        print("\tStarted ABC")
        dots = dict()

        # Start a process for the ABC tool
        process = pexpect.spawn(config.abc_cmd, cwd=str(config.abc_path))

        # Careful: the command "collapse" renames output variables to intermediate node names
        process.sendline('read "{}"; collapse;'.format(self.benchmark.file_path.name))

        try:
            if config.time_limit_bdd is not None:
                index = process.expect(['abc 03'], timeout=config.time_limit_bdd)
            else:
                index = process.expect(['abc 03'])

            output_variables = list(self.benchmark.get_output_variables())

            if index == 0:
                if not self.multi_output:
                    for i in range(len(output_variables)):
                        output_variable = output_variables[i]
                        print("\t\tOutput variable {}/{}: {}".format(i + 1, len(output_variables), output_variable))
                        process.sendline('show_bdd "{}";'.format(output_variable))
                        dot = self._read_file(output_variable)
                        dots[output_variable] = dot
                else:
                    process.sendline('show_bdd -g;')
                    dot = self._read_file()
                    dots[self.benchmark.name] = dot
                print("\tStopped ABC")
        except EOF:
            raise Exception("\tABC EOF error.\n")
        except TIMEOUT:
            # TODO: Log
            # self.log["bdd_time"] = config.time_limit_bdd
            # self.log["status"] = "timeout"
            # config.log.add_json(self.get_log())
            raise Exception("\tABC timeout error.\n")
        return dots

    def _read_file(self, output_variable: str = None) -> str:
        """
        Reads the DOT content from the copy file.
        :return:
        """
        dot = ""
        while not self.dot_file.exists():
            pass
        time.sleep(1)

        with open(self.dot_file, 'r') as file:
            for line in file:
                dot += line

        if output_variable is not None:
            dot = re.sub(" {2}\w+ {2}", "  {0}  ".format(output_variable), dot)

        if self.dot_file.exists():
            os.remove(self.dot_file)
        while self.dot_file.exists():
            pass
        time.sleep(1)
        return dot

    def parse(self) -> BDDCollection:
        """
        Parses the benchmark.
        First, the benchmark is written to a file in the ABC directory.
        Then, the DOT files are generated and read from file.
        Finally, the DOT files are converted into BDDs.
        :return:
        """
        print("Started constructing BDD from benchmark")

        self.benchmark.write(self.abc_file_path)

        dots = self._write_dot()
        for name, dot in dots.items():
            bdd = self._parse_dot(dot, name)
            self.dd_collection.add(bdd)

        # Remove the file from the abc folder
        os.remove(self.abc_file_path)

        # config.log.add_json(self.get_log())
        print("Stopped constructing BDD from benchmark")
        print()

        return self.dd_collection
