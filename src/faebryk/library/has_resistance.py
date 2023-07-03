from abc import abstractmethod

from faebryk.core.core import ModuleTrait


class has_resistance(ModuleTrait):
    @abstractmethod
    def get_resistance(self):
        ...
