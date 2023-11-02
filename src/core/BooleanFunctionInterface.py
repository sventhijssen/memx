from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Dict, Set


class BooleanFunctionInterface(ABC):
    """
    An interface for a multi-output Boolean function.
    """

    @abstractmethod
    def get_input_variables(self) -> Set[str]:
        """
        Returns the set of input variables of this multi-output Boolean function.
        """
        pass

    @abstractmethod
    def get_output_variables(self) -> Set[str]:
        """
        Returns the set of output variables of this multi-output Boolean function.
        """
        pass

    @abstractmethod
    def get_auxiliary_variables(self) -> Set[str]:
        """
        Returns the set of auxiliary variables of this multi-output Boolean function.
        """
        pass

    @abstractmethod
    def eval(self, instance: Dict[str, bool]) -> Dict[str, bool]:
        """
        Given the instance, this function returns an evaluation of this multi-output Boolean function.
        An evaluation is an assignment for each variable to a Boolean truth value (true/false).
        :param instance: A dictionary mapping the input variables (str) to the Boolean truth values true and false (bool).
        :return: A dictionary mapping the output variables (str) to the Boolean truth values true and false (bool).
        """
        pass
