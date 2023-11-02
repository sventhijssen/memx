from abc import ABC, abstractmethod

from core.BooleanFunction import BooleanFunction


class Parser(ABC):

    def __init__(self):
        super().__init__()

    @abstractmethod
    def parse(self) -> BooleanFunction:
        pass
