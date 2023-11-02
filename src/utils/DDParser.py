from abc import abstractmethod, ABC

from core.benchmarks.Benchmark import Benchmark
from core.decision_diagrams.DDCollection import DDCollection


class DDParser(ABC):

    def __init__(self, benchmark: Benchmark):
        super().__init__()
        self.benchmark = benchmark
        self.dd_collection = DDCollection()
        self.dd_construct_time = None
        self.dd_show_times = dict()

    @abstractmethod
    def parse(self) -> DDCollection:
        pass
