from abc import ABC, abstractmethod


class DrawInterface(ABC):

    @abstractmethod
    def to_dot(self) -> str:
        pass
