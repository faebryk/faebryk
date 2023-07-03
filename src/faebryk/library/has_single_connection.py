from abc import abstractmethod

from faebryk.core.core import InterfaceTrait, Link


class has_single_connection(InterfaceTrait):
    @abstractmethod
    def get_connection(self) -> Link:
        ...
