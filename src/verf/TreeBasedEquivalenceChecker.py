from abc import abstractmethod
from typing import List

from z3 import Bool

from core.benchmarks.Benchmark import VerilogBenchmark
from core.hardware.Crossbar import MemristorCrossbar
from verf.GraphBasedEquivalenceChecker import GraphBasedEquivalenceChecker


class TreeBasedEquivalenceChecker(GraphBasedEquivalenceChecker):

    def __init__(self, crossbar: MemristorCrossbar, specification: VerilogBenchmark):
        super().__init__(crossbar, specification)
        self.trees = dict()

    @abstractmethod
    def to_formula(self, output_variable: str) -> Bool:
        pass

    def get_simple_paths(self, output_variable: str) -> List[List[str]]:
        if output_variable not in self.trees:
            return []
        stack = [self.trees[output_variable]]

        if self.trees[output_variable] is None:
            return []

        simple_paths = []
        while len(stack) != 0:
            tree = stack.pop()
            for child_key in tree.children.keys():
                child_nodes = tree.children[child_key]
                for child_node in child_nodes:
                    if child_node["output"]:
                        simple_paths.append(child_node["path"])
                    else:
                        stack.append(child_node["subtree"])
        return simple_paths
