from abc import ABC, abstractmethod
from pathlib import Path

from core.BooleanFunction import BooleanFunction


class IOInterface(ABC):

    @abstractmethod
    def to_string(self) -> str:
        pass

    @staticmethod
    @abstractmethod
    def from_string(content: str) -> BooleanFunction:
        pass

    @staticmethod
    @abstractmethod
    def read(filepath: Path) -> BooleanFunction:
        pass

    def write(self, file_path: Path):
        with open(file_path, 'w') as f:
            content = self.to_string()
            f.write(content)
