from __future__ import annotations
from typing import Dict, Set

from core.BooleanFunction import BooleanFunction


class Formula(BooleanFunction):

    def __init__(self, verilog: VerilogFormula):
        super().__init__()
        self.verilog = verilog

    @staticmethod
    def get_file_extension() -> str:
        raise NotImplementedError()

    def get_input_variables(self) -> Set[str]:
        return self.verilog.boolean_expression.get_input_variables()

    def get_output_variables(self) -> Set[str]:
        return set(self.verilog.output)

    def get_auxiliary_variables(self) -> Set[str]:
        return set()

    def negate(self) -> Formula:
        """
        Returns the negation of this formula.
        """
        return self.__neg__()

    def __str__(self):
        return str(self.verilog.output) + ' = ' + str(self.verilog.boolean_expression)

    def __repr__(self):
        return str(self.verilog.output) + ' = ' + str(self.verilog.boolean_expression)

    def __neg__(self):
        return Formula(self.verilog.negate())

    def eval(self, instance: Dict[str, bool]) -> Dict[str, bool]:
        return {self.verilog.output: self.verilog.boolean_expression.eval(instance)}


class VerilogFormula:

    def __init__(self):
        self.output = None
        self.boolean_expression = None

    def negate(self):
        neg_verilog_formula = VerilogFormula()
        neg_verilog_formula.output = self.output
        neg_verilog_formula.boolean_expression = self.boolean_expression.negate()
        return neg_verilog_formula
