from __future__ import annotations

from abc import ABC, abstractmethod
from functools import reduce
from typing import Dict, Set

from z3 import Bool, Not, Xor, Or, And, If


class BooleanExpression(ABC):

    @staticmethod
    def _tree_to_boolean_expression(lst) -> BooleanExpression:
        """
        Returns a Verilog syntax tree to a BooleanExpression.
        :param lst:
        :return:
        """
        if not lst:
            return Or()

        if isinstance(lst, str):
            if lst == "1'b0":
                return FALSE()
            elif lst == "1'b1":
                return TRUE()
            if lst[0] == '~':
                return LITERAL(lst[1:], False)
            return LITERAL(lst, True)
        if len(lst) == 1:
            return BooleanExpression._tree_to_boolean_expression(lst[0])
        elif len(lst) >= 5 and lst[1] == '?':
            cond = lst[0]
            true_stmt = lst[2]
            false_stmt = lst[4]
            return IF(BooleanExpression._tree_to_boolean_expression(cond),
                      BooleanExpression._tree_to_boolean_expression(true_stmt),
                      BooleanExpression._tree_to_boolean_expression(false_stmt))
        elif len(lst) > 3:
            # Precedence order: NOT > AND > XOR > OR
            # https://stackoverflow.com/questions/12494568/boolean-operators-precedence#:~:text=There%20are%20three%20basic%20Boolean%20operators%3A%20NOT%2C%20AND%2C,have%20common%20precedence%3A%20NOT%20%3E%20AND%20%3E%20OR.
            # First, we find the operators, their indices, and then we group their arguments.

            # All odd elements should be an operator. Further, this operator should be the same for all indices.
            op = lst[1]
            for i in range(3, len(lst), 2):
                if lst[i] != op:
                    raise Exception("Operator should be same for all indices.")
            if op == '^':
                expressions = [lst[i] for i in range(0, len(lst), 2)]
                xor_expressions = set(map(lambda e: BooleanExpression._tree_to_boolean_expression(e), expressions))
                return XOR(xor_expressions)
            elif op == '&':
                expressions = [lst[i] for i in range(0, len(lst), 2)]
                and_expressions = set(map(lambda e: BooleanExpression._tree_to_boolean_expression(e), expressions))
                return AND(and_expressions)
            elif op == '|':
                expressions = [lst[i] for i in range(0, len(lst), 2)]
                or_expressions = set(map(lambda e: BooleanExpression._tree_to_boolean_expression(e), expressions))
                return OR(or_expressions)
            else:
                raise Exception("Other operator than expected.")
            # raise NotImplementedError()
        elif len(lst) >= 3 and lst[1] == '^':
            expressions = [lst[i] for i in range(0, len(lst), 2)]
            xor_expressions = set(map(lambda e: BooleanExpression._tree_to_boolean_expression(e), expressions))
            return XOR(xor_expressions)
        elif len(lst) >= 3 and lst[1] == '&':
            expressions = [lst[i] for i in range(0, len(lst), 2)]
            and_expressions = set(map(lambda e: BooleanExpression._tree_to_boolean_expression(e), expressions))
            return AND(and_expressions)
        elif len(lst) >= 3 and lst[1] == '|':
            expressions = [lst[i] for i in range(0, len(lst), 2)]
            or_expressions = set(map(lambda e: BooleanExpression._tree_to_boolean_expression(e), expressions))
            return OR(or_expressions)
        raise Exception("Unexpected operator.")

    @staticmethod
    def _verilog_to_tree(verilog_formula: str):
        # Begin Source
        # URL: https://stackoverflow.com/questions/37925803/parserelement-enablepackrat-doesnt-make-infixnotation-faster
        # Author: PaulMcG
        # Published on: June 20, 2016
        # Accessed on: July 15, 2020
        # Begin Source (2): https://stackoverflow.com/questions/23879784/parse-mathematical-expressions-with-pyparsing
        # Author: PaulMcG
        # Published on: May 20, 2014
        # Visited on: July 15, 2020
        from pyparsing import Suppress, Forward, Word, alphanums, Group, ZeroOrMore, oneOf, Literal

        LPAR, RPAR = map(Suppress, '()')
        expr = Forward()
        variable = Word(alphanums + '_' '~' '[' ']')
        nested = Literal("1'b0") | Literal("1'b1") | variable | Group(LPAR + expr + RPAR)
        binary_op = nested + ZeroOrMore(oneOf('^ | &') + nested)
        ternary_op = nested + Literal('?') + nested + Literal(':') + nested
        formula_expr = ternary_op | binary_op
        expr <<= formula_expr
        tree = [expr.parseString(verilog_formula).asList()]
        # End Source

        return tree

    @abstractmethod
    def __copy__(self):
        pass

    def copy(self):
        return self.__copy__()

    @staticmethod
    def read(formula: str) -> BooleanExpression:
        tree = BooleanExpression._verilog_to_tree(formula)
        return BooleanExpression._tree_to_boolean_expression(tree)

    @abstractmethod
    def get_input_variables(self) -> Set[str]:
        pass

    @abstractmethod
    def to_z3(self) -> Bool:
        pass

    @abstractmethod
    def negate(self) -> BooleanExpression:
        pass

    @abstractmethod
    def fix(self, atom: str, positive: bool) -> BooleanExpression:
        pass

    @abstractmethod
    def substitute(self, original: LITERAL, replacement: BooleanExpression) -> BooleanExpression:
        pass

    @abstractmethod
    def simplify(self) -> BooleanExpression:
        pass

    @abstractmethod
    def eval(self, instance: Dict[str, bool]) -> bool:
        pass


class AND(BooleanExpression):

    def __init__(self, expressions: Set[BooleanExpression]):
        super().__init__()
        self.expressions = expressions

    def __copy__(self):
        return AND(self.expressions.copy())

    def __str__(self):
        if len(self.expressions) == 1:
            return str(list(self.expressions)[0])
        return "(" + " & ".join(map(lambda e: str(e), self.expressions)) + ")"

    def get_input_variables(self) -> Set[str]:
        return reduce(lambda e0, e1: e0.union(e1), map(lambda e: e.get_input_variables(), self.expressions))

    def to_z3(self) -> Bool:
        return And(*list(map(lambda e: e.to_z3(), self.expressions)))

    def fix(self, atom: str, positive: bool) -> BooleanExpression:
        expressions = set()
        for expression in self.expressions:
            expressions.add(expression.fix(atom, positive))
        return AND(expressions)

    def substitute(self, original: LITERAL, replacement: BooleanExpression) -> BooleanExpression:
        expressions = set()
        for expression in self.expressions:
            expressions.add(expression.substitute(original, replacement))
        return AND(expressions)

    def simplify(self) -> BooleanExpression:
        """
        TODO: Flatten a conjunction of conjunctions
        e.g. (A & B) & (C & D) & (E & F) = A & B & C & D & E & F
        :return:
        """
        simplified_expressions = list(map(lambda e: e.simplify(), self.expressions))
        for expression in simplified_expressions:
            if expression.negate() in simplified_expressions:
                return FALSE()
        return self

    def negate(self) -> BooleanExpression:
        return OR(set(map(lambda x: x.negate(), self.expressions)))

    def eval(self, instance: Dict[str, bool]) -> bool:
        return reduce(lambda e0, e1: e0 and e1, map(lambda e: e.eval(instance), self.expressions))


class OR(BooleanExpression):

    def __init__(self, expressions: Set[BooleanExpression]):
        super().__init__()
        self.expressions = expressions

    def __copy__(self):
        return OR(self.expressions.copy())

    def __str__(self):
        if len(self.expressions) == 1:
            return str(list(self.expressions)[0])
        return "(" + " | ".join(map(lambda e: str(e), self.expressions)) + ")"

    def get_input_variables(self) -> Set[str]:
        return reduce(lambda e0, e1: e0.union(e1), map(lambda e: e.get_input_variables(), self.expressions))

    def to_z3(self) -> Bool:
        return Or(*list(map(lambda e: e.to_z3(), self.expressions)))

    def fix(self, atom: str, positive: bool) -> BooleanExpression:
        expressions = set()
        for expression in self.expressions:
            expressions.add(expression.fix(atom, positive))
        return OR(expressions)

    def substitute(self, original: LITERAL, replacement: BooleanExpression) -> BooleanExpression:
        expressions = set()
        for expression in self.expressions:
            expressions.add(expression.substitute(original, replacement))
        return OR(expressions)

    def simplify(self) -> BooleanExpression:
        self.expressions = set(map(lambda e: e.simplify(), self.expressions))
        if TRUE() in self.expressions:
            return TRUE()
        return self

    def negate(self) -> BooleanExpression:
        return AND(set(map(lambda x: x.negate(), self.expressions)))

    def eval(self, instance: Dict[str, bool]) -> bool:
        return reduce(lambda e0, e1: e0 or e1, map(lambda e: e.eval(instance), self.expressions))


class NOT(BooleanExpression):

    def __init__(self, expression: BooleanExpression):
        self.expression = expression

    def __copy__(self):
        return NOT(self.expression.copy())

    def __str__(self):
        if isinstance(self.expression, LITERAL):
            return "~{}".format(self.expression)
        return "~({})".format(self.expression)

    def get_input_variables(self) -> Set[str]:
        return self.expression.get_input_variables()

    def to_z3(self) -> Bool:
        return Not(self.expression.to_z3())

    def eval(self, instance: Dict[str, bool]) -> bool:
        raise not self.expression.eval(instance)

    def negate(self) -> BooleanExpression:
        return self.expression

    def fix(self, atom: str, positive: bool) -> BooleanExpression:
        return NOT(self.expression.fix(atom, positive))

    def substitute(self, original: LITERAL, replacement: BooleanExpression) -> BooleanExpression:
        return NOT(self.expression.substitute(original, replacement))

    def simplify(self) -> BooleanExpression:
        return self.expression.negate()


class XOR(BooleanExpression):

    def __init__(self, expressions: Set[BooleanExpression]):
        super().__init__()
        self.expressions = expressions

    def __copy__(self):
        return XOR(self.expressions.copy())

    def __str__(self):
        return "(" + " ^ ".join(map(lambda e: str(e), self.expressions)) + ")"

    def get_input_variables(self) -> Set[str]:
        return reduce(lambda e0, e1: e0.union(e1), map(lambda e: e.get_input_variables(), self.expressions))

    def to_z3(self) -> Bool:
        return Xor(*list(map(lambda e: e.to_z3(), self.expressions)))

    def fix(self, atom: str, positive: bool) -> BooleanExpression:
        expressions = set()
        for expression in self.expressions:
            expressions.add(expression.fix(atom, positive))
        return XOR(expressions)

    def substitute(self, original: LITERAL, replacement: BooleanExpression) -> BooleanExpression:
        expressions = set()
        for expression in self.expressions:
            expressions.add(expression.substitute(original, replacement))
        return XOR(expressions)

    def simplify(self) -> BooleanExpression:
        """
        To simplify a XOR operations over a set of sub-expressions, we do the following after [1]:
        Let E = [e_0, e_1, ..., e_n] be an ordered list of the sub-expressions e_i.
        While the length of the list is greater than two, we apply the XOR operation over the list in a recursive manner.
        We group the first n elements ([e_0, ..., e_(n-1)]) as one factor, and exclude e_n.
        Then, we apply the XOR over these two factors [e_0, ..., e_(n-1)] and e_n.
        We recursively apply this to the list until we arrive at the base case.
        [1] https://math.stackexchange.com/questions/2480640/boolean-expression-of-3-input-xor-gate
        :return:
        """
        e = list(self.expressions)
        e_n = e[-1]
        if len(self.expressions) >= 2:
            e_0_n = XOR(set(e[:-1]))
            a = AND({OR({e_0_n, e_n}), OR({NOT(e_0_n), NOT(e_n)})})
            print("--{} {}\t\t{}".format(e_0_n, e_n, a))
            return a.simplify()
        return e[0].simplify()

    def negate(self) -> BooleanExpression:
        return self.simplify().negate()

    def eval(self, instance: Dict[str, bool]) -> bool:
        return reduce(lambda e0, e1: e0 ^ e1, map(lambda e: e.eval(instance), self.expressions))


class IF(BooleanExpression):

    def __init__(self, condition: BooleanExpression, true_expression: BooleanExpression,
                 false_expression: BooleanExpression):
        self.condition = condition
        self.true_expression = true_expression
        self.false_expression = false_expression

    def __copy__(self):
        return IF(self.condition.copy(), self.true_expression.copy(), self.false_expression.copy())

    def __str__(self):
        return "(({}) ? ({}) : ({}))".format(self.condition, self.true_expression, self.false_expression)

    def get_input_variables(self) -> Set[str]:
        return self.condition.get_input_variables().union(self.true_expression.get_input_variables()).union(
            self.false_expression.get_input_variables())

    def to_z3(self) -> Bool:
        return If(self.condition.to_z3(), self.true_expression.to_z3(), self.false_expression.to_z3())

    def negate(self) -> BooleanExpression:
        return If(self.condition, self.false_expression, self.true_expression)

    def fix(self, atom: str, positive: bool) -> BooleanExpression:
        condition = self.condition.fix(atom, positive)
        true_expression = self.true_expression.fix(atom, positive)
        false_expression = self.false_expression.fix(atom, positive)
        return IF(condition, true_expression, false_expression)

    def substitute(self, original: LITERAL, replacement: BooleanExpression) -> BooleanExpression:
        condition = self.condition.substitute(original, replacement)
        true_expression = self.true_expression.substitute(original, replacement)
        false_expression = self.false_expression.substitute(original, replacement)
        return IF(condition, true_expression, false_expression)

    def simplify(self) -> BooleanExpression:
        raise NotImplementedError()

    def eval(self, instance: Dict[str, bool]) -> bool:
        if self.condition.eval(instance):
            return self.true_expression.eval(instance)
        return self.false_expression.eval(instance)


class LITERAL(BooleanExpression):

    def __init__(self, name: str, positive: bool = True):
        super().__init__()
        self.atom = name
        self.positive = positive

    def __copy__(self):
        return LITERAL(self.atom, self.positive)

    def __str__(self):
        if self.positive and self.atom == "True":
            return "1'b1"
        if not self.positive and self.atom == "False":
            return "1'b0"
        if self.positive:
            return str(self.atom)
        elif self.atom == 'False':
            return str(self.atom)
        else:
            return "~" + str(self.atom)

    def __repr__(self):
        if self.positive and self.atom == "True":
            return str(1)
        if not self.positive and self.atom == "False":
            return str(0)
        if self.positive:
            return str(self.atom)
        elif self.atom == 'False':
            return str(self.atom)
        else:
            return "~" + str(self.atom)

    def __eq__(self, other):
        if isinstance(other, LITERAL):
            return self.atom == other.atom and self.positive == other.positive
        return False

    def __hash__(self):
        return hash(self.atom)

    def get_input_variables(self) -> Set[str]:
        return {self.atom}

    def to_z3(self) -> Bool:
        if not self.positive:
            return Not(Bool(self.atom))
        return Bool(self.atom)

    def fix(self, atom: str, positive: bool) -> LITERAL:
        if self.atom == atom:
            if self.positive == positive:
                return TRUE()
            return FALSE()
        return self

    def substitute(self, original: LITERAL, replacement: BooleanExpression) -> BooleanExpression:
        if self.atom == original.atom:
            if self.positive:
                return replacement
            return NOT(replacement)
        return self.copy()

    def simplify(self) -> BooleanExpression:
        return self

    def negate(self):
        if self.positive:
            return LITERAL(self.atom, False)
        return LITERAL(self.atom, True)

    def eval(self, instance: Dict[str, bool]) -> bool:
        if self.atom == "True":
            return True
        elif self.atom == "False":
            return False

        if self.positive:
            truth_value = instance.get(self.atom)
        else:
            truth_value = not instance.get(self.atom)
        return truth_value


class TRUE(LITERAL):

    def __init__(self):
        super().__init__("True", True)

    def __copy__(self):
        return TRUE()

    def __str__(self):
        return "1'b1"

    def __repr__(self):
        return "1"

    def get_input_variables(self) -> Set[str]:
        return set()

    def to_z3(self) -> Bool:
        return True

    def negate(self) -> BooleanExpression:
        return FALSE()

    def fix(self, literal: LITERAL, positive: bool) -> LITERAL:
        return self

    def substitute(self, original: LITERAL, replacement: BooleanExpression) -> BooleanExpression:
        return self

    def simplify(self) -> BooleanExpression:
        return self

    def eval(self, instance: Dict[str, bool]) -> bool:
        return True


class FALSE(LITERAL):

    def __init__(self):
        super().__init__("False", False)

    def __copy__(self):
        return FALSE()

    def __str__(self):
        return "1'b0"

    def __repr__(self):
        return "0"

    def get_input_variables(self) -> Set[str]:
        return set()

    def to_z3(self) -> Bool:
        return False

    def negate(self) -> BooleanExpression:
        return TRUE()

    def fix(self, atom: str, positive: bool) -> LITERAL:
        return self

    def substitute(self, original: LITERAL, replacement: BooleanExpression) -> BooleanExpression:
        return self

    def simplify(self) -> BooleanExpression:
        return self

    def eval(self, instance: Dict[str, bool]) -> bool:
        return False
