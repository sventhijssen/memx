from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Dict, Any, List


class Loggable(ABC):

    def __init__(self):
        self.log = dict()

    @abstractmethod
    def get_log(self) -> List[Dict[str, Any]] | Dict[str, Any]:
        pass
