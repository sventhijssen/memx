import time

import pexpect
from blifparser.keywords.generic import Blif, Model, Inputs, Outputs
from networkx import topological_sort
from pexpect import EOF, TIMEOUT

from utils import config
from utils.BDDDOTParser import BDDDOTParser
from utils.DDParser import DDParser
from core.benchmarks.Benchmark import Benchmark, BLIFBenchmark
from core.decision_diagrams.BDD import BDD
from core.decision_diagrams.BDDTopology import BDDTopology


class KLUTParser(DDParser):

    def __init__(self, benchmark: Benchmark, K: int, G: int):
        super().__init__(benchmark)
        self.K = K
        self.G = G
        self.blif_file = config.abc_path.joinpath("{}.blif".format(self.benchmark.name))
        self.sub_blif_file = config.abc_path.joinpath("copy.blif")
        self.abc_file_path = config.abc_path.joinpath(self.benchmark.file_path.name)
        self.start_time = None
        self.end_time = None

    def _write_klut(self) -> BLIFBenchmark:
        """
        Writes the BLIF content using the ABC tool.
        :return: Returns a BLIF benchmark (k-LUT)
        """
        print("\tStarted ABC")

        # Start a process for the ABC tool
        process = pexpect.spawn(config.abc_cmd, cwd=str(config.abc_path))

        # Careful: the command "collapse" renames output variables to intermediate node names
        arguments = []
        if self.K:
            arguments.append("-K")
            arguments.append(str(self.K))
        if self.G:
            arguments.append("-G")
            arguments.append(str(self.G))
        arguments_str = " ".join(arguments)
        cmd = 'read "{}"; if {}; write_blif "{}";'.format(self.benchmark.file_path.name, arguments_str, self.blif_file.name)
        process.sendline(cmd)

        blif_benchmark = None
        try:
            index = process.expect(['abc 03'])
            if index == 0:
                blif_benchmark = BLIFBenchmark.read(self.blif_file)

                # if self.blif_file.exists():
                #     os.remove(self.blif_file)

            print("\tStopped ABC")
        except EOF:
            raise Exception("\tABC EOF error.\n")
        except TIMEOUT:
            raise Exception("\tABC timeout error.\n")
        return blif_benchmark

    def parse(self) -> BDDTopology:
        print("Started constructing k-LUT from benchmark")

        self.start_time = time.time()

        json_content = dict()

        self.benchmark.write(self.abc_file_path)

        blif_benchmark = self._write_klut()

        graph = blif_benchmark.to_data_flow_graph()
        bdds = dict()
        for output in topological_sort(graph):
            # If the node is a primary input variable, then we must not evaluate it.
            if output in blif_benchmark.get_input_variables():
                continue

            boolean_function = blif_benchmark.functions.get(output)
            blif = Blif()
            blif.model = Model(boolean_function.output)
            if len(boolean_function.inputs) == 0:
                blif.inputs = Inputs("False")
            else:
                blif.inputs = Inputs(" ".join(boolean_function.inputs))
            blif.outputs = Outputs("{}".format(boolean_function.output))
            blif.booleanfunctions = [boolean_function]
            sub_blif_benchmark = BLIFBenchmark(blif, file_path = self.sub_blif_file, name=output)
            parser = BDDDOTParser(sub_blif_benchmark)
            bdd_collection = parser.parse()
            bdd = list(bdd_collection.boolean_functions)[0]

            assert isinstance(output, str)
            assert isinstance(bdd, BDD)

            bdds[output] = bdd

        bdd_topology = BDDTopology(graph, bdds)

        # if self.abc_file_path.exists():
        #     os.remove(self.abc_file_path)

        self.end_time = time.time()

        json_content["klutparser"] = {
            "total_time": self.end_time - self.start_time
        }

        config.log.add_json(json_content)

        return bdd_topology
