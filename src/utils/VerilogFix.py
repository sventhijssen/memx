from pathlib import Path
from typing import List

from core.benchmarks.Benchmark import VerilogBenchmark
from core.expressions.BooleanExpression import LITERAL


class VerilogFix:

    def __init__(self, specification: VerilogBenchmark, fixed_file_path: Path):
        self.specification = specification
        self.fixed_file_path = fixed_file_path

    def fix(self, literals: List[LITERAL]):
        with open(self.fixed_file_path, 'w') as f:
            self.specification.write(self.fixed_file_path)

        with open(self.fixed_file_path, 'r') as f:
            verilog_content = f.read()

        pre, post = verilog_content.split("output ")

        nextchars = [')', ' ', ';']
        for literal in literals:
            for nextchar in nextchars:
                atom = literal.atom
                positive = literal.positive
                if not positive:
                    post = post.replace('~' + atom + nextchar, "1'b1" + nextchar)
                else:
                    post = post.replace('~' + atom + nextchar, "1'b0" + nextchar)
                if not positive:
                    post = post.replace(atom + nextchar, "1'b0" + nextchar)
                else:
                    post = post.replace(atom + nextchar, "1'b1" + nextchar)

        verilog_content = pre + "output " + post

        with open(self.fixed_file_path, 'w') as f:
            f.write(verilog_content)