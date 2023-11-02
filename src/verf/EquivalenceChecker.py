from abc import ABC, abstractmethod

from timeout_decorator import timeout_decorator
from z3 import Bool

from utils import config
from core.BooleanFunctionInterface import BooleanFunctionInterface


class EquivalenceChecker(ABC):

    @abstractmethod
    def __init__(self, boolean_function: BooleanFunctionInterface, specification: BooleanFunctionInterface):
        self.boolean_function = boolean_function
        self.specification = specification
        self.execution_time = []
        self.formulae = dict()  # A dictionary <output_variable: str, formula: Bool>
        self.simple_paths = dict()  # A dictionary <output_variable: str, simple_paths: List[List[str]]>
        # By default, we want to collect the formulae. However, this can be computationally expensive for
        # GraphBasedEquivalenceChecker (see more info in class). Hence, we provide a setting to toggle
        # whether we want to return the formulae or not.
        self.return_formulae = True
        self.formula_sizes = dict()
        self.nr_simple_paths = dict()

    def get_execution_time(self):
        return self.execution_time

    @abstractmethod
    @timeout_decorator.timeout(config.equivalence_checker_timeout)
    def is_equivalent(self, sampling_size: int = 0) -> bool:
        pass

    @abstractmethod
    def to_formula(self, output_variable: str) -> Bool:
        pass
