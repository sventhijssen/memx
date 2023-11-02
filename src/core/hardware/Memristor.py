from typing import Dict, Set

from z3 import Bool

from core.expressions.BooleanExpression import LITERAL, BooleanExpression


class Memristor(BooleanExpression):
    """
    A memristor is a programmable device with a resistive state.
    The device can be assigned a Boolean literal, and can consequently be programmed to either a
    low resistive state (ON/True/1) or a high resistive state (OFF/False/0).
    """

    def __init__(self, row: int, column: int, literal: LITERAL, layer: int = 0, stuck_at_fault: LITERAL = None):
        """
        Constructs a memristor object for given literal at the given row, column, and layer.
        :param row: The given row in the crossbar.
        :param column: The given column in the crossbar.
        :param literal: The given literal to be assigned to this memristor.
        :param layer: The given layer in the crossbar.
        """
        super().__init__()
        self.row = row
        self.column = column
        self.layer = layer
        self.literal = literal
        self.stuck_at_fault = stuck_at_fault

    def __copy__(self):
        return Memristor(self.row, self.column, self.literal.copy(), self.layer, self.stuck_at_fault.copy())

    def __str__(self):
        return str(self.literal)

    def __repr__(self):
        return str(self.literal)

    def get_input_variables(self) -> Set[str]:
        return self.literal.get_input_variables()

    def to_z3(self) -> Bool:
        if self.stuck_at_fault is not None:
            return self.stuck_at_fault.to_z3()
        return self.literal.to_z3()

    def negate(self) -> BooleanExpression:
        if self.stuck_at_fault is not None:
            return self.stuck_at_fault
        return self.literal.negate()

    def fix(self, atom: str, positive: bool) -> BooleanExpression:
        raise NotImplementedError()

    def substitute(self, original: LITERAL, replacement: BooleanExpression) -> BooleanExpression:
        raise NotImplementedError()

    def simplify(self) -> BooleanExpression:
        raise NotImplementedError()

    def eval(self, instance: Dict[str, bool]) -> bool:
        if self.stuck_at_fault is not None:
            return self.stuck_at_fault.eval(instance)
        return self.literal.eval(instance)
