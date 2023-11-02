from abc import ABC

from core.BooleanFunction import BooleanFunction
from core.DrawInterface import DrawInterface
from core.IOInterface import IOInterface


class Component(BooleanFunction, IOInterface, DrawInterface, ABC):

    pass
