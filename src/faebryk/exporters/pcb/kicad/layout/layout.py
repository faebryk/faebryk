from abc import abstractmethod

from faebryk.core.core import Node


class Layout:
    @abstractmethod
    def apply(self, node: Node): ...
