from __future__ import annotations

import os
from abc import ABC, abstractmethod
from functools import reduce
from pathlib import Path
from typing import Dict, Any, Set, List

from blifparser.blifparser import BlifParser
from blifparser.keywords.generic import Blif, Names
from networkx import topological_sort, DiGraph
from z3 import Bool

from Loggable import Loggable
from utils import config
from utils.PLAParser import PLA, PLAParser
from utils.VerilogParser import VerilogModule, VerilogParser
from core.BooleanFunction import BooleanFunction
from core.IOInterface import IOInterface
from core.benchmarks.Formula import Formula, VerilogFormula
from core.expressions.BooleanExpression import LITERAL


class Benchmark(BooleanFunction, Loggable, IOInterface, ABC):
    """
    An abstract class to represent a benchmark. A benchmark is a multi-output Boolean function.
    """

    def __init__(self, file_path: Path = None, name: str = None):
        """
        A benchmark has optionally a file path and a name.
        :param file_path: Optionally, a file path for the benchmark.
        :param name: Optionally, a name for the benchmark.
        """
        super().__init__()
        self.file_path = file_path
        self._set_name(file_path, name)

    def get_log(self) -> List[Dict[str, Any]] | Dict[str, Any]:
        return {
            "type": self.__class__.__name__,
            "inputs": len(self.get_input_variables()),
            "outputs": len(self.get_output_variables()),
            "wires": len(self.get_auxiliary_variables())
        }

    def _set_name(self, file_path: Path, name: str):
        """
        Sets the name for the benchmark based on the given file path or the given name.
        If no name is provided, then the stem of the file path is used as name for this benchmark.
        Otherwise, the given name is used for this benchmark.
        :param file_path: The file path of the benchmark.
        :param name: The name of the benchmark.
        :return:
        """
        if name is None:
            if file_path is None:
                self.name = ""
            else:
                self.name = file_path.stem
        else:
            self.name = name

    def _abc_conversion(self, original_filename: str, new_filename: str, write_cmd: str):
        import time
        import pexpect

        abc_original_path = config.abc_path.joinpath(original_filename)
        abc_new_path = config.abc_path.joinpath(new_filename)

        self.write(abc_original_path)

        time.sleep(2)

        process = pexpect.spawn(config.abc_cmd, cwd=str(config.abc_path))
        process.sendline('read "{}"; {} "{}";'.format(original_filename, write_cmd, new_filename))

        while not abc_new_path.exists():
            pass

        time.sleep(2)

        benchmark = Benchmark.read(abc_new_path)

        os.remove(abc_original_path)

        return benchmark

    @abstractmethod
    def to_blif(self) -> BLIFBenchmark:
        pass

    @abstractmethod
    def to_pla(self) -> PLABenchmark:
        pass

    @abstractmethod
    def to_verilog(self) -> VerilogBenchmark:
        pass


class BLIFBenchmark(Benchmark, Loggable):
    """
    A class to represent a BLIF benchmark.
    """

    def __init__(self, blif: Blif, file_path: Path = None, name: str = None):
        """
        A BLIF benchmark has the BLIF content, and optionally a file path and a name.
        :param blif: The BLIF content.
        :param file_path: Optionally, a file path for the benchmark.
        :param name: Optionally, a name for the benchmark.
        """
        super().__init__(file_path, name)
        self.blif = blif
        self.functions = self._get_functions()

    @staticmethod
    def get_file_extension() -> str:
        return "blif"

    def get_input_variables(self) -> Set[str]:
        return self.blif.inputs.inputs

    def get_output_variables(self) -> Set[str]:
        return self.blif.outputs.outputs

    def get_auxiliary_variables(self) -> Set[str]:
        output_variables = self.get_output_variables()
        auxiliary_variables = set()
        for bf in self.blif.booleanfunctions:
            if bf.output not in output_variables:
                auxiliary_variables.add(bf.output)
        return auxiliary_variables

    def model_name(self) -> str:
        """
        Returns the name of this BLIF benchmark.
        :return: The name of this BLIF benchmark.
        """
        if self.name:
            return self.name
        return self.blif.model.name

    @staticmethod
    def from_string(content: str) -> BooleanFunction:
        raise NotImplementedError()

    @staticmethod
    def read(file_path: Path) -> BLIFBenchmark:
        """
        Reads a BLIF benchmark from the file with the given file path.
        :param file_path: The path of the BLIF file.
        :return: A BLIF benchmark.
        """
        parser = BlifParser(str(file_path))
        blif = parser.blif
        name = blif.model.name
        return BLIFBenchmark(blif, file_path, name)

    def to_file_path(self, file_name: str):
        return Path(file_name + '.' + self.get_file_extension())

    def to_string(self) -> str:
        content = ""
        content += ".model {}\n".format(self.model_name())
        content += ".inputs {}\n".format(" ".join(self.get_input_variables()))
        content += ".outputs {}\n".format(" ".join(self.get_output_variables()))
        for _, names in self.functions.items():
            content += str(names)
        content += ".end"
        return content

    def _get_functions(self) -> Dict[str, Names]:
        """
        Returns the wordlines of this BLIF benchmark.
        Here, a function is a dictionary with the output as key and the names as value.
        :return: A dictionary mapping the output to the names.
        """

        functions = dict()
        for bf in self.blif.booleanfunctions:
            functions[bf.output] = bf
        return functions

    def eval(self, instance: Dict[str, bool]) -> Dict[str, bool]:
        evaluations = dict()
        evaluations.update(instance)

        graph = self.to_data_flow_graph()
        for node in topological_sort(graph):
            # If the node is a primary input variable, then we must not evaluate it.
            if node in self.get_input_variables():
                continue
            else:
                names = self.functions.get(node)
                inputs = names.inputs
                truthtable = names.truthtable

                line_evaluations = []
                for line in truthtable:
                    line_evaluation = []
                    for i in range(len(inputs)):
                        variable = inputs[i]
                        variable_value = evaluations.get(variable)
                        raw_truthtable_value = line[i]

                        if raw_truthtable_value == "~" or raw_truthtable_value == "-":
                            continue
                        elif raw_truthtable_value == "0":
                            truthtable_value = False
                        elif raw_truthtable_value == "1":
                            truthtable_value = True
                        else:
                            raise Exception("Unknown truth value for input variable {}".format(variable))

                        line_evaluation.append(variable_value == truthtable_value)

                    line_evaluations.append(reduce(lambda x, y: x and y, line_evaluation))
                evaluation = reduce(lambda x, y: x or y, line_evaluations)
                evaluations[node] = evaluation

        # We remove the primary input variables and the auxiliary variables from the evaluation
        # such that we only retain the primary output variables.
        for input_variable in self.get_input_variables():
            evaluations.pop(input_variable)
        for auxiliary_variable in self.get_auxiliary_variables():
            evaluations.pop(auxiliary_variable)

        return evaluations

    def to_data_flow_graph(self) -> DiGraph():
        """
        Returns a data flow graph of this BLIF benchmark.
        The leaf nodes are the primary input variables, and the root nodes are the output variables.
        """
        graph = DiGraph()
        for output_variable, names in self.functions.items():
            graph.add_node(output_variable)
            for input_variable in names.inputs:
                graph.add_node(input_variable)
                graph.add_edge(input_variable, output_variable)
        return graph

    def to_blif(self) -> BLIFBenchmark:
        return self

    def to_pla(self) -> PLABenchmark:
        self._abc_conversion("x.blif", "x.pla", "write_pla")
        pla_benchmark = PLABenchmark.read(config.abc_path.joinpath("x.pla"))
        abc_new_path = config.abc_path.joinpath("x.pla")
        os.remove(abc_new_path)
        return pla_benchmark

    def to_verilog(self) -> VerilogBenchmark:
        self._abc_conversion("x.blif", "x.v", "write_verilog")
        verilog_benchmark = VerilogBenchmark.read(config.abc_path.joinpath("x.v"))
        abc_new_path = config.abc_path.joinpath("x.v")
        os.remove(abc_new_path)
        return verilog_benchmark


class PLABenchmark(Benchmark):
    """
    A class to represent a PLA benchmark.
    """

    def __init__(self, pla: PLA, file_path: Path = None, name: str = None):
        """
        A PLA benchmark has the PLA content, and optionally a file path and auxiliary variables.
        :param pla: The PLA content.
        :param file_path: Optionally, a file path for the benchmark.
        :param name: Optionally, a name for the benchmark.
        """
        self.pla = pla
        super().__init__(file_path, name)

    def get_file_extension(self) -> str:
        return "pla"

    def get_input_variables(self) -> Set[str]:
        return set(self.pla.inputs)

    def get_output_variables(self) -> Set[str]:
        return set(self.pla.outputs)

    def get_auxiliary_variables(self) -> Set[str]:
        return set()

    @staticmethod
    def from_string(content: str) -> BooleanFunction:
        raise NotImplementedError()

    @staticmethod
    def read(file_path: Path) -> PLABenchmark:
        pla_parser = PLAParser(file_path)
        pla = pla_parser.pla
        return PLABenchmark(pla, file_path=file_path)

    def to_string(self) -> str:
        content = ""
        content += ".i {}\n".format(len(self.get_input_variables()))
        content += ".o {}\n".format(len(self.get_output_variables()))
        content += ".ilb {}\n".format(" ".join(self.pla.inputs))
        content += ".ob {}\n".format(" ".join(self.pla.outputs))
        content += ".p {}\n".format(len(self.pla.truthtable))
        for (input_vector, output_vector) in self.pla.truthtable:
            content += "{} {}\n".format("".join(input_vector), "".join(output_vector))
        content += ".e"
        return content

    def _satisfies(self, input_vector: List[str], instance: Dict[str, bool]) -> bool:
        """
        Auxiliary function for the evaluation of a PLA benchmark.
        Returns true if and only if the given input vector satisfies the given instance.
        An input vector satisfies the given instance when there is no conflict among the truth values.
        A conflict arises when we have a pair of (True, False) or (False, True) for the input vector and the instance,
        i.e. when input_variable_value != truth_table_value.
        :param input_vector: The input vector of the truth table of this PLA benchmark.
        :param instance: The given input vector.
        :return:
        """

        # We iterate over each input variable
        for i in range(len(self.pla.inputs)):
            input_variable = self.pla.inputs[i]

            # We get the truth value from the instance
            input_variable_value = instance.get(input_variable)
            # We get the truth value from the truth table of this PLA benchmark
            raw_truthtable_value = input_vector[i]

            if raw_truthtable_value == "~" or raw_truthtable_value == "-":
                continue
            elif raw_truthtable_value == "0":
                truth_table_value = False
            elif raw_truthtable_value == "1":
                truth_table_value = True
            else:
                raise Exception("Unknown truth value for input variable {}".format(input_variable))

            if input_variable_value != truth_table_value:
                return False

        return True

    def eval(self, instance: Dict[str, bool]) -> Dict[str, bool]:
        evaluations = dict()

        # Initially, every output variable is False
        for output_variable in self.get_output_variables():
            evaluations[output_variable] = False

        # We iterate over the lines in the truth table
        for line in self.pla.truthtable:
            input_vector, output_vector = line

            # When the input vector of the line satisfies the given instance,
            # then we will determine the evaluation of the output variables
            # based on the corresponding output vector.
            if self._satisfies(input_vector, instance):

                # We iterate over the output variables in the line
                for i in range(len(self.pla.outputs)):
                    output_variable = self.pla.outputs[i]
                    raw_truthtable_value = output_vector[i]

                    # When we find that an output variable evaluates to true, we use it for the evaluation.
                    # An output variable evaluating to True cannot be undone, i.e. when the entry is False,
                    # we leave the evaluation untouched.
                    if raw_truthtable_value == "~" or raw_truthtable_value == "-":
                        continue
                    elif raw_truthtable_value == "0":
                        continue
                    elif raw_truthtable_value == "1":
                        evaluations[output_variable] = True
                    else:
                        raise Exception("Unknown truth value for input variable {}".format(output_variable))

        return evaluations

    def to_blif(self) -> BLIFBenchmark:
        self._abc_conversion("x.pla", "x.blif", "write_blif")
        blif_benchmark = BLIFBenchmark.read(config.abc_path.joinpath("x.blif"))
        abc_new_path = config.abc_path.joinpath("x.blif")
        os.remove(abc_new_path)
        return blif_benchmark

    def to_pla(self) -> PLABenchmark:
        return self

    def to_verilog(self) -> VerilogBenchmark:
        self._abc_conversion("x.pla", "x.v", "write_verilog")
        verilog_benchmark = VerilogBenchmark.read(config.abc_path.joinpath("x.v"))
        abc_new_path = config.abc_path.joinpath("x.v")
        os.remove(abc_new_path)
        return verilog_benchmark


class VerilogBenchmark(Benchmark):
    """
    A class to represent a Verilog benchmark.
    """

    def __init__(self, verilog: VerilogModule, file_path: Path = None, name: str = None):
        """
        A Verilog benchmark has the Verilog content, and optionally a file path and name.
        :param verilog: The Verilog content.
        :param file_path: Optionally, a file path for the benchmark.
        :param name: Optionally, a name for the benchmark.
        """
        super().__init__(file_path, name)
        self.verilog = verilog

    @staticmethod
    def get_file_extension() -> str:
        return "v"

    def __copy__(self):
        return VerilogBenchmark(self.verilog.copy(), self.file_path, self.name)

    def get_input_variables(self) -> Set[str]:
        return self.verilog.inputs

    def get_output_variables(self) -> Set[str]:
        return self.verilog.outputs

    def get_auxiliary_variables(self) -> Set[str]:
        return self.verilog.wires

    # TODO: Fix! This can be achieved using VerilogFix in aux folder.
    def fix(self, atom: str, positive: bool) -> VerilogBenchmark:
        raise NotImplementedError()

    def negate(self) -> VerilogBenchmark:
        """
        Returns the negation of this benchmark.
        """

        negated_functions = dict()
        for variable, formula in self.verilog.functions.items():
            if variable in self.get_output_variables():
                negated_formula = formula.negate()
                negated_functions[variable] = negated_formula
            else:
                negated_functions[variable] = formula

        name = self.name + "_neg"
        input_variables = self.get_input_variables()
        output_variables = self.get_output_variables()
        auxiliary_variables = self.get_auxiliary_variables()
        file_path = self.file_path

        verilog = VerilogModule()
        verilog.module_name = name
        verilog.inputs = input_variables
        verilog.wires = auxiliary_variables
        verilog.outputs = output_variables
        verilog.functions = negated_functions

        return VerilogBenchmark(verilog, file_path, name)

    @staticmethod
    def from_string(content: str) -> BooleanFunction:
        raise NotImplementedError()

    @staticmethod
    def read(file_path: Path) -> VerilogBenchmark:
        verilog_parser = VerilogParser(file_path)
        verilog = verilog_parser.verilog_module
        return VerilogBenchmark(verilog, file_path, verilog.module_name)

    def eval(self, instance: Dict[str, bool]) -> Dict[str, bool]:
        evaluations = dict()
        evaluations.update(instance)

        graph = self._to_data_flow_graph()
        for node in topological_sort(graph):
            # If the node is a primary input variable, then we must not evaluate it.
            if node in self.get_input_variables():
                continue
            else:
                formula = self.verilog.functions.get(node)
                evaluations[node] = formula.eval(evaluations).get(node)

        # We remove the primary input variables and the auxiliary variables from the evaluation
        # such that we only retain the primary output variables.
        for input_variable in self.get_input_variables():
            evaluations.pop(input_variable)
        for auxiliary_variable in self.get_auxiliary_variables():
            evaluations.pop(auxiliary_variable)

        return evaluations

    def _to_data_flow_graph(self) -> DiGraph():
        """
        Returns a data flow graph of this Verilog benchmark.
        The leaf nodes are the primary input variables, and the root nodes are the output variables.
        """
        graph = DiGraph()
        for output_variable, formula in self.verilog.functions.items():
            graph.add_node(output_variable)
            for input_variable in formula.get_input_variables():
                graph.add_node(input_variable)
                graph.add_edge(input_variable, output_variable)
        return graph

    def to_string(self) -> str:
        input_variables = ", ".join(sorted(self.get_input_variables()))
        output_variables = ", ".join(sorted(self.get_output_variables()))

        content = "module {} (".format(self.verilog.module_name)
        content += "\n"
        content += "\t{}, {});".format(input_variables, output_variables)
        content += "\n"
        content += "\tinput {};".format(input_variables)
        content += "\n"
        content += "\toutput {};".format(output_variables)
        content += "\n"
        if len(self.get_auxiliary_variables()) > 0:
            auxiliary_variables = ", ".join(sorted(self.get_auxiliary_variables()))
            content += "\twire {};".format(auxiliary_variables)
            content += "\n"
        for function_name, formula in self.verilog.functions.items():
            content += "\tassign {};".format(formula)
            content += "\n"
        content += "endmodule"
        return content

    def collapse(self) -> VerilogBenchmark:
        data_flow_graph = self._to_data_flow_graph()  # From primary input variable to output variable
        node_to_expression = dict()
        for node in topological_sort(data_flow_graph):
            if len(data_flow_graph.in_edges(node)) == 0:
                node_to_expression[node] = LITERAL(node, True)
            else:
                formula = self.verilog.functions.get(node)
                boolean_expression = formula.verilog.boolean_expression
                # print("Node: {}".format(node))
                # print(boolean_expression)
                for (child_node, _) in data_flow_graph.in_edges(node):
                    child_expression = node_to_expression.get(child_node)
                    # print("\t{} -> \t{}".format(child_node, child_expression))
                    boolean_expression = boolean_expression.substitute(LITERAL(child_node, True), child_expression)
                node_to_expression[node] = boolean_expression

        functions = dict()
        for output_variable in self.get_output_variables():
            verilog = VerilogFormula()
            verilog.output = output_variable
            verilog.boolean_expression = node_to_expression.get(output_variable)
            formula = Formula(verilog)
            functions[output_variable] = formula

        verilog_module = VerilogModule()
        verilog_module.module_name = self.verilog.module_name
        verilog_module.inputs = self.verilog.inputs
        verilog_module.outputs = self.verilog.outputs
        verilog_module.wires = set()
        verilog_module.functions = functions

        return VerilogBenchmark(verilog_module)

    def to_z3(self) -> Dict[str, Bool]:
        verilog_benchmark = self.collapse()
        functions = dict()
        for output_variable, formula in verilog_benchmark.verilog.functions.items():
            functions[output_variable] = formula.verilog.boolean_expression.to_z3()
        return functions

    def to_blif(self, collapse: bool = True) -> BLIFBenchmark:
        self._abc_conversion("x.v", "x.blif", "write_blif")
        blif_benchmark = BLIFBenchmark.read(config.abc_path.joinpath("x.blif"))
        abc_new_path = config.abc_path.joinpath("x.blif")
        os.remove(abc_new_path)
        return blif_benchmark

    def to_pla(self) -> PLABenchmark:
        self._abc_conversion("x.v", "x.pla", "write_pla")
        pla_benchmark = PLABenchmark.read(config.abc_path.joinpath("x.pla"))
        abc_new_path = config.abc_path.joinpath("x.pla")
        os.remove(abc_new_path)
        return pla_benchmark

    def to_verilog(self) -> VerilogBenchmark:
        return self
