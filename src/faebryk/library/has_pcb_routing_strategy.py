# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

from abc import abstractmethod

from faebryk.core.core import ModuleTrait
from faebryk.exporters.pcb.kicad.transformer import PCB_Transformer


class has_pcb_routing_strategy(ModuleTrait):
    @abstractmethod
    def calculate(self): ...

    # TODO remove transformer from here
    @abstractmethod
    def apply(self, transformer: PCB_Transformer): ...
