import multiprocessing
import time
from abc import abstractmethod
from typing import List

from z3 import Solver, Not, unsat, Bool

from utils import Z3Tools, config
from utils.Log import Log
from utils.Z3Converter import Z3Converter
from core.benchmarks.Benchmark import VerilogBenchmark
from core.hardware.Crossbar import MemristorCrossbar
from verf.Enumeration import Enumeration
from verf.EquivalenceChecker import EquivalenceChecker


class GraphBasedEquivalenceChecker(EquivalenceChecker):

    def __init__(self, crossbar: MemristorCrossbar, specification: VerilogBenchmark):
        super().__init__(crossbar, specification)
        self.trees = dict()
        self.enum_log = Log(config.log.log_file_name[:-4] + "_enum.log")
        self.graph_log = Log(config.log.log_file_name[:-4] + "_graph.log")

    @abstractmethod
    def get_simple_paths(self, output_variable: str) -> List[List[str]]:
        pass

    @abstractmethod
    def to_formula(self, output_variable: str) -> Bool:
        pass

    # def _enumeration_parallel(self, event, sampling_size, queue):
    def _enumeration_parallel(self, event, sampling_size):
        assert isinstance(self.specification, VerilogBenchmark)

        self.enum_log.add("enum\n")

        # Start timing
        start_time = time.time()

        # Run enumeration
        enumeration = Enumeration(self.boolean_function, self.specification)
        equivalent = enumeration.is_equivalent(sampling_size)

        # Stop timing
        stop_time = time.time()
        execution_time = stop_time - start_time

        # When sampling results in non-equivalence, then the answer is conclusive.
        # Otherwise, when sampling results in equivalence, then the answer is inconclusive.
        if not equivalent:
            # queue.put({"name": "enum", "equivalent": equivalent, "nr_input_vectors": enumeration.nr_input_vectors, "execution_time": execution_time})
            self.enum_log.add("equivalent: false\n")
            self.enum_log.add("nr_input_vectors: {}\n".format(enumeration.nr_input_vectors))
            self.enum_log.add("execution_time: {}\n".format(execution_time))
            event.set()
        self.enum_log.add("equivalent: inconclusive\n")
        self.enum_log.add("nr_input_vectors: {}\n".format(enumeration.nr_input_vectors))
        self.enum_log.add("execution_time: {}\n".format(execution_time))

    # def _graph_based_parallel(self, event, queue):
    def _graph_based_parallel(self, event):
        assert isinstance(self.specification, VerilogBenchmark)

        self.graph_log.add("graph\n")

        total_extract_time = 0
        total_check_time = 0
        total_nr_paths = 0
        total_nr_literals = 0

        for (output_variable, verilog_formula) in self.specification.verilog.functions.items():
            z3_benchmark_formula = Z3Converter.verilog_to_z3(verilog_formula.verilog_module)

            # Start timing extraction
            start_time = time.time()

            z3_crossbar_formula = self.to_formula(output_variable)

            # Stop timing extraction
            stop_time = time.time()
            extraction_time = stop_time - start_time
            total_extract_time += extraction_time

            # Start timing verification
            start_time = time.time()

            f = z3_benchmark_formula == z3_crossbar_formula

            s = Solver()
            s.add(Not(f))
            if s.check() == unsat:
                print("output variable {}: equivalent".format(output_variable))
                self.graph_log.add("equivalent {}: true\n".format(output_variable))

                # Stop timing verification
                stop_time = time.time()
                check_time = stop_time - start_time
                total_check_time += check_time

                print("extraction_time {}: {}".format(output_variable, extraction_time))
                print("check_time {}: {}".format(output_variable, check_time))
                self.graph_log.add("extraction_time {}: {}\n".format(output_variable, extraction_time))
                self.graph_log.add("check_time {}: {}\n".format(output_variable, check_time))

                if config.record_formulae:
                    # Get number of simple paths from formula
                    nr_paths = len(self.get_simple_paths(output_variable))
                    total_nr_paths += nr_paths

                    # Get number of selectorlines from formula
                    nr_literals = len(Z3Tools.get_literals(z3_crossbar_formula))
                    total_nr_literals += nr_literals
            else:
                print("Output variable {}: NOT equivalent".format(output_variable))
                self.graph_log.add("equivalent {}: false\n".format(output_variable))

                # Stop timing verification
                stop_time = time.time()
                check_time = stop_time - start_time
                total_check_time += check_time

                if config.record_formulae:
                    # Get number of simple paths from formula
                    nr_paths = len(self.get_simple_paths(output_variable))
                    total_nr_paths += nr_paths

                    # Get number of selectorlines from formula
                    nr_literals = len(Z3Tools.get_literals(z3_crossbar_formula))
                    total_nr_literals += nr_literals

                print("extraction_time {}: {}".format(output_variable, extraction_time))
                print("check_time {}: {}".format(output_variable, check_time))
                self.graph_log.add("extraction_time {}: {}\n".format(output_variable, extraction_time))
                self.graph_log.add("check_time {}: {}\n".format(output_variable, check_time))

                self.graph_log.add("equivalent: false\n")
                self.graph_log.add("total_nr_paths: {}\n".format(total_nr_paths))
                self.graph_log.add("total_nr_literals: {}\n".format(total_nr_literals))
                self.graph_log.add("total_extraction_time: {}\n".format(total_extract_time))
                self.graph_log.add("total_check_time: {}\n".format(total_check_time))

                # queue.put({"name": "graph", "equivalent": False, "nr_paths": total_nr_paths, "size:": total_nr_literals, "extraction_time": total_extract_time, "check_time": total_check_time})
                event.set()

        self.graph_log.add("equivalent: true\n")
        self.graph_log.add("total_nr_paths: {}\n".format(total_nr_paths))
        self.graph_log.add("total_nr_literals: {}\n".format(total_nr_literals))
        self.graph_log.add("total_extraction_time: {}\n".format(total_extract_time))
        self.graph_log.add("total_check_time: {}\n".format(total_check_time))

        # queue.put({"name": "graph", "equivalent": True, "nr_paths": total_nr_paths, "size": total_nr_literals, "extraction_time": total_extract_time, "check_time": total_check_time})
        event.set()

    def _graph_based(self):
        assert isinstance(self.specification, VerilogBenchmark)

        z3c = Z3Converter()

        extraction_times = dict()
        check_times = dict()

        formulae = dict()
        simple_paths = dict()

        for (output_variable, z3_benchmark_formula) in self.specification.to_z3().items():
            start_time = time.time()
            z3_crossbar_formula = self.to_formula(output_variable)
            end_time = time.time()
            formulae[output_variable] = z3_crossbar_formula
            simple_paths[output_variable] = self.get_simple_paths(output_variable)
            extraction_time = end_time - start_time
            extraction_times[output_variable] = extraction_time

            f = z3_benchmark_formula == z3_crossbar_formula

            start_time = time.time()
            s = Solver()
            s.add(Not(f))
            if s.check() == unsat:
                print("Output variable {}: equivalent".format(output_variable))
                config.log.add("Equivalent {}: true\n".format(output_variable))
            else:
                print("Output variable {}: NOT equivalent".format(output_variable))
                config.log.add("Equivalent {}: false\n".format(output_variable))

                end_time = time.time()
                check_time = end_time - start_time
                check_times[output_variable] = check_time
                print("Extraction time {}: {}".format(output_variable, extraction_time))
                print("Check time {}: {}".format(output_variable, check_time))
                config.log.add("Extraction time {}: {}\n".format(output_variable, extraction_time))
                config.log.add("Check time {}: {}\n".format(output_variable, check_time))
                for (output_variable, formula) in formulae.items():
                    formulae[output_variable] = Z3Converter.z3_to_str(formula)
                return False
            end_time = time.time()
            check_time = end_time - start_time
            check_times[output_variable] = check_time
            print("Extraction time {}: {}".format(output_variable, extraction_time))
            print("Check time {}: {}".format(output_variable, check_time))
            config.log.add("Extraction time {}: {}\n".format(output_variable, extraction_time))
            config.log.add("Check time {}: {}\n".format(output_variable, check_time))
        return True

    def is_equivalent(self, sampling_size: int = 0) -> bool:
        # If the sampling size is zero, then we do not run in sampling parallel.
        if sampling_size == 0:
            return self._graph_based()

        config.log.add("enum: {}\n".format(self.enum_log.log_file_name))
        config.log.add("graph: {}\n".format(self.graph_log.log_file_name))

        # Based on answer:
        # https://stackoverflow.com/questions/47903791/how-to-terminate-a-multiprocess-in-python-when-a-given-condition-is-met
        # AND:
        # https://stackoverflow.com/questions/43289199/python-multiprocessing-queue-get-and-put
        processes = set()

        # Store process information
        # queue = multiprocessing.Queue()

        # Event to trigger termination of processes
        event = multiprocessing.Event()

        # Enumeration process
        # enumeration = multiprocessing.Process(target=self._enumeration_parallel, args=(event, sampling_size, queue))
        enumeration = multiprocessing.Process(target=self._enumeration_parallel, args=(event, sampling_size))
        enumeration.start()
        processes.add(enumeration)

        # Graph-based process
        # graph_based = multiprocessing.Process(target=self._graph_based_parallel, args=(event, queue))
        graph_based = multiprocessing.Process(target=self._graph_based_parallel, args=(event,))
        graph_based.start()
        processes.add(graph_based)

        # When the event is set, we terminate all processes
        while True:
            if event.is_set():
                for process in processes:
                    process.terminate()
                    # https://stackoverflow.com/questions/60721574/python-multiprocessing-after-kill-process-give-is-alive-status-true
                    process.join(timeout=1.0)
                    print(process.is_alive())
                break
        # result = queue.get()
        # print(result)
        return False
