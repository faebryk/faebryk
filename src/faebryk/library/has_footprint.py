from abc import abstractmethod

from faebryk.core.core import Footprint, ModuleTrait


class has_footprint(ModuleTrait):
    @abstractmethod
    def get_footprint(self) -> Footprint:
        ...
