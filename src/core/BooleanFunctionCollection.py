from pathlib import Path
from typing import Dict, Set, Any

from Loggable import Loggable
from core.BooleanFunction import BooleanFunction
from core.BooleanFunctionInterface import BooleanFunctionInterface


class BooleanFunctionCollection(BooleanFunctionInterface, Loggable):
    """
    A class to represent a set of multi-output Boolean functions.
    """

    def __init__(self, boolean_functions: Set[BooleanFunction] = None):
        """
        A multi-output Boolean function collection is a set of multi-output Boolean functions.
        """
        super().__init__()
        if boolean_functions is None:
            boolean_functions = set()
        self.boolean_functions = boolean_functions

    def copy(self):
        return self.__copy__()

    def __copy__(self):
        return BooleanFunctionCollection(self.boolean_functions.copy())

    def get_log(self) -> Dict[str, Any]:
        return {

        }

    def add(self, boolean_function: BooleanFunction):
        """
        Adds a multi-output Boolean function to this
        :param boolean_function:
        :return:
        """
        self.boolean_functions.add(boolean_function)

    def get_input_variables(self) -> Set[str]:
        """
        Returns the set of input variables of this multi-output Boolean function.
        """
        input_variables = set()
        for boolean_function in self.boolean_functions:
            input_variables.update(boolean_function.get_input_variables())
        return input_variables

    def get_output_variables(self) -> Set[str]:
        """
        Returns the set of output variables of this multi-output Boolean function.
        """
        output_variables = set()
        for boolean_function in self.boolean_functions:
            output_variables.update(boolean_function.get_output_variables())
        return output_variables

    def get_auxiliary_variables(self) -> Set[str]:
        auxiliary_variables = set()
        for boolean_function in self.boolean_functions:
            auxiliary_variables.update(boolean_function.get_auxiliary_variables())
        return auxiliary_variables

    def get_boolean_functions(self) -> Set[BooleanFunction]:
        return self.boolean_functions

    @staticmethod
    def read(file_path: Path) -> BooleanFunctionInterface:
        raise NotImplementedError()

    def to_json(self) -> Dict[Any, Any]:
        return {
            "boolean_functions": [boolean_function.to_json() for boolean_function in self.boolean_functions]
        }

    def to_string(self) -> str:
        return " \n".join([boolean_function.to_string() for boolean_function in self.boolean_functions])

    def write(self, file_path: Path = None):
        content = self.to_string()
        with open(file_path, "w") as f:
            f.write(content)

    def draw(self) -> Set[str]:
        content = set()
        for boolean_function in self.boolean_functions:
            sub_content = boolean_function.draw()
            content.update(sub_content)
        return content

    def eval(self, instance: Dict[str, bool]) -> Dict[str, bool]:
        content = dict()
        for boolean_function in self.boolean_functions:
            sub_content = boolean_function.eval(instance)
            for key, value in sub_content.items():
                content[key] = value
        return content
