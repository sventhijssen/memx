from __future__ import annotations

from pathlib import Path
from typing import Set

from core.BooleanFunctionCollection import BooleanFunctionCollection
from core.decision_diagrams.DD import DD


class DDCollection(BooleanFunctionCollection):

    def __init__(self, dds: Set[DD] = None):
        super().__init__(dds)

    def get_input_variables(self) -> Set[str]:
        raise NotImplementedError()

    def get_output_variables(self) -> Set[str]:
        raise NotImplementedError()

    def get_auxiliary_variables(self) -> Set[str]:
        raise NotImplementedError()

    @staticmethod
    def read(file_path: Path) -> BooleanFunctionCollection:
        raise NotImplementedError()

    def to_string(self) -> str:
        content = ""
        for dd in self.boolean_functions:
            content += dd.to_string()
        return content

    def add(self, dd: DD):
        super().add(dd)

    def prune(self) -> DDCollection:
        new_dd_collection = DDCollection()
        for dd in self.boolean_functions:
            new_dd = dd.prune()
            new_dd_collection.add(new_dd)
        return new_dd_collection
