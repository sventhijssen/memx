import re
from pathlib import Path

from core.benchmarks.Formula import Formula, VerilogFormula
from core.expressions.BooleanExpression import BooleanExpression


class VerilogModule:

    def __init__(self):
        self.module_name = None
        self.inputs = None
        self.wires = None
        self.outputs = None
        self.functions = None

    def __copy__(self):
        verilog_module = VerilogModule()
        verilog_module.module_name = self.module_name
        verilog_module.inputs = self.inputs
        verilog_module.outputs = self.outputs
        verilog_module.functions = self.functions
        return verilog_module

    def copy(self):
        return self.__copy__()


class VerilogParser:

    def __init__(self, file_path: Path):
        self.verilog_module = VerilogModule()

        with open(file_path, 'r') as f:
            content = f.read()

        # TODO: Find a better solution for handling these arrays
        content = content.replace('\\', '').replace('[', '').replace(']', '')

        matches = re.findall(r'module\s+(.+)\s+\(', content)
        module_name = matches[0].replace(' ', '')

        match = re.search(r'input([.\r\n]*[^;])+', content)
        if match is None:
            all_input_variables = set()
        else:
            raw_input_variables = match.group()
            all_input_variables = raw_input_variables.replace('input', '').replace('\n', ' ').replace(' ', '').split(
                ',')

        match = re.search(r'output([.\r\n]*[^;])+', content)
        raw_output_variables = match.group()
        output_variables = raw_output_variables.replace('output', '').replace('\n', ' ').replace(' ', '').split(',')

        match = re.search(r'wire([.\r\n]*[^;])+', content)
        if match:
            raw_auxiliary_variables = match.group()
            auxiliary_variables = raw_auxiliary_variables.replace('wire', '').replace('\n', ' ').replace(' ', '').split(
                ',')
        else:
            auxiliary_variables = []

        assignments = re.findall(r'assign\s+(.+)\s+=\s+(.+);', content)

        functions = dict()
        for assignment in assignments:
            (raw_function_name, raw_formula) = assignment
            function_name = raw_function_name.replace(' ', '')
            input_variables = []
            for input_variable in all_input_variables:
                if input_variable in raw_formula:
                    input_variables.append(input_variable)
            for auxiliary_variable in auxiliary_variables:
                if auxiliary_variable in raw_formula:
                    input_variables.append(auxiliary_variable)
            verilog = VerilogFormula()
            verilog.output = function_name
            verilog.boolean_expression = BooleanExpression.read(raw_formula)
            formula = Formula(verilog)
            functions[function_name] = formula

        self.verilog_module.module_name = module_name
        self.verilog_module.inputs = all_input_variables
        self.verilog_module.wires = auxiliary_variables
        self.verilog_module.outputs = output_variables
        self.verilog_module.functions = functions
