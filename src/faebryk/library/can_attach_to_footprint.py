from abc import abstractmethod

from faebryk.core.core import Footprint, ModuleTrait


class can_attach_to_footprint(ModuleTrait):
    @abstractmethod
    def attach(self, footprint: Footprint):
        ...
