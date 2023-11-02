from pathlib import Path
from typing import List, Dict, Any

from networkx import DiGraph, set_node_attributes

from core.expressions.BooleanExpression import LITERAL


class BDDModule:

    def __init__(self):
        self.module_name = None
        self.inputs = None
        self.outputs = None
        self.dag = None
        self.variable_order = None


class BDDParser:
    """
    A class to parse a BDD from a BDD file.
    """

    def __init__(self, file_path: Path):
        super().__init__()

        with open(file_path, 'r') as f:
            content = f.read()

        self.bdd_module = self.from_string(content)

    @staticmethod
    def from_string(content: str) -> BDDModule:
        bdd_module = BDDModule()

        keywords = ["model", "inputs", "outputs", "order", "bdd"]
        raw_lines = content.split("\n")

        # We strip the comment lines
        lines = []
        for line in raw_lines:
            if not line.startswith("#"):
                lines.append(line)

        components = dict()
        current_keyword = None
        halt = False
        for i in range(len(lines)):
            if halt:
                break
            line = lines[i]
            for keyword in keywords:
                if halt:
                    break
                if line.startswith(".{}".format(keyword)):
                    components[keyword] = [i]
                    if current_keyword is not None:
                        components[current_keyword].append(i - 1)
                    current_keyword = keyword

                    if keyword == "bdd":
                        halt = True

        module_name_range = components.get("model")
        bdd_module.module_name = lines[module_name_range[0]][7:]
        variable_order_range = components.get("order")
        for line_index in range(variable_order_range[0], variable_order_range[1] + 1):
            line = lines[line_index]
            bdd_module.variable_order = line.split()[1:]

        lines = lines[components["bdd"][0]:]

        node_attrs = dict()
        dag = None
        for i in range(len(lines)):
            line = lines[i]
            if len(line) == 0:
                continue
            elif line.startswith(".bdd"):
                dag = DiGraph()
            elif line.startswith(".end"):
                set_node_attributes(dag, node_attrs)
                bdd_module.dag = dag
                break
            else:
                line_items = line.split()

                if line_items[1] != '-1':
                    dag.add_edge(line_items[0], line_items[1], literal=LITERAL(line_items[3], True))
                if line_items[2] != '-1':
                    dag.add_edge(line_items[0], line_items[2], literal=LITERAL(line_items[3], False))

                output_variables = set()
                for output_variable in line_items[4:]:
                    output_variables.add(output_variable)

                node_attrs[line_items[0]] = {
                    "terminal": line_items[3] == '1' or line_items[3] == '0',
                    "root": len(output_variables) > 0,
                    "variable": line_items[3],
                    "output_variables": output_variables
                }

        return bdd_module

    def get_log(self) -> Dict[str, Any]:
        return {
            
        }

    @staticmethod
    def _prettify(lines: List, components: Dict, keyword: str):
        [start, stop] = components.get(keyword)
        raw_content = lines[start:stop + 1]
        raw_content = ''.join(raw_content)
        return raw_content.replace(".{}".format(keyword), "").replace("\\", "")