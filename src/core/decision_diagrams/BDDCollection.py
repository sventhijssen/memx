from __future__ import annotations

from pathlib import Path
from typing import List, Dict, Set, Any

from core.decision_diagrams.BDD import BDD
from core.decision_diagrams.DDCollection import DDCollection


class BDDCollection(DDCollection):

    def __init__(self, bdds: Set[BDD] = None):
        super().__init__(bdds)

    def get_input_variables(self) -> Set[str]:
        raise NotImplementedError()

    def get_output_variables(self) -> Set[str]:
        raise NotImplementedError()

    def get_auxiliary_variables(self) -> Set[str]:
        raise NotImplementedError()

    @staticmethod
    def _prettify(lines: List, components: Dict, keyword: str):
        [start, stop] = components.get(keyword)
        raw_content = lines[start:stop + 1]
        raw_content = ''.join(raw_content)
        return raw_content.replace(".{}".format(keyword), "").replace("\\", "")

    @staticmethod
    def read(file_path: Path) -> BDDCollection:
        all_bdd_content = set()
        with open(file_path, 'r') as f:
            lines = f.readlines()

        bdd_content = None
        for line in lines:
            if line.startswith(".model"):
                if bdd_content is None:
                    bdd_content = line
                else:
                    all_bdd_content.add(bdd_content)
                    bdd_content = line
            else:
                bdd_content += line
        all_bdd_content.add(bdd_content)

        bdds = set()
        for bdd_content in all_bdd_content:
            bdd = BDD.from_string(bdd_content)
            bdds.add(bdd)
        return BDDCollection(bdds)

    def write(self, file_path: Path) -> Dict[str, Any]:
        content = ""
        for bdd in self.boolean_functions:
            sub_content = list(bdd.write())[0]
            content += sub_content
            content += "\n"
        with open(file_path, "w") as f:
            f.write(content)
            f.write("\n")
