from abc import ABC, abstractmethod

from networkx import DiGraph

from Loggable import Loggable
from core.hardware.Topology import Topology


class PartitioningMethod(Loggable, ABC):

    def __init__(self, graph: DiGraph, **kwargs):
        super().__init__()
        self.graph = graph
        self.topology = None
        self.start_time = None
        self.end_time = None

    @abstractmethod
    def partition(self) -> Topology:
        pass
