# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

from abc import abstractmethod

from faebryk.core.core import ModuleInterface, ModuleTrait


class has_pin_association_heuristic(ModuleTrait):
    @abstractmethod
    def get_pin(self, str) -> ModuleInterface: ...
