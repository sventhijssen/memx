import re
from pathlib import Path
from typing import List, Dict


class PLA:
    def __init__(self):
        """
        .i 3
        .o 2
        .ilb a b cin
        .ob cout s    #This is a comment
        .type f
        .phase 111
        000 00
        001 01
        010 01
        011 10
        100 01
        101 10
        110 10
        111 11
        .e
        """
        self.inputs = None
        self.outputs = None
        self.truthtable = None

        self.nkeywords = {
            ".ilb": 0,
            ".ob": 0,
            ".i": 0,
            ".o": 0,
            ".p": 0,
            ".e": 0,
        }


class PLAParser:

    def __init__(self, file_path: Path):
        self.pla = PLA()

        with open(file_path, 'r') as f:
            content = f.read()

        # Important: ilb and ob do not always exist.
        # ABC will automatically generate input variables and output variables.
        # If .i = PI and .ilb is absent, then the input variables are of the form:
        # x0 x1 ... xPI
        # If .o = PI and .ob is absent, then the output variables are of the form:
        # z0 z1 ... zPI
        keywords = ["ilb", "ob", "i", "o", "p"]
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
                    break
                elif not line.startswith('.') and not line.startswith('#'):
                    if current_keyword is not None:
                        components[current_keyword].append(i - 1)
                    halt = True

        input_variables = []
        output_variables = []
        for keyword in keywords:
            if keyword == "ilb" and keyword in components:
                pretty_content = self._prettify(lines, components, keyword)
                input_variables = re.findall(r'([\w\d\[\]]+)', pretty_content)
            elif keyword == "ob" and keyword in components:
                pretty_content = self._prettify(lines, components, keyword)
                output_variables = re.findall(r'([\w\d\[\]]+)', pretty_content)
            elif keyword == "i" and "ilb" not in components:
                pretty_content = self._prettify(lines, components, keyword)
                nr_inputs = int(re.findall(r'(\d+)', pretty_content)[0])
                nr_char = len(str(nr_inputs - 1))
                fmt = '0{}d'.format(nr_char)
                input_variables = [f'x{i:{fmt}}' for i in range(nr_inputs)]
            elif keyword == "o" and "ob" not in components:
                pretty_content = self._prettify(lines, components, keyword)
                nr_outputs = int(re.findall(r'(\d+)', pretty_content)[0])
                nr_char = len(str(nr_outputs - 1))
                fmt = '0{}d'.format(nr_char)
                output_variables = [f'z{i:{fmt}}' for i in range(nr_outputs)]

        truthtable = []
        for line in lines:
            if not line.startswith(".") and not line.startswith("#") and line != "":
                [inputs, outputs] = line.split()
                truthtable.append(([v for v in inputs], [v for v in outputs]))

        self.pla.inputs = input_variables
        self.pla.outputs = output_variables
        self.pla.truthtable = truthtable

    @staticmethod
    def _prettify(lines: List, components: Dict, keyword: str):
        [start, stop] = components.get(keyword)
        raw_content = lines[start:stop + 1]
        raw_content = ''.join(raw_content)
        return raw_content.replace(".{}".format(keyword), "").replace("\\", "")