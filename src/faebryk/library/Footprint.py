# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

from typing import Generic, TypeVar

from faebryk.core.core import Module, ModuleInterface, _ModuleTrait
from faebryk.library.Electrical import Electrical

TF = TypeVar("TF", bound="Footprint")


class _FootprintTrait(Generic[TF], _ModuleTrait[TF]): ...


class FootprintTrait(_FootprintTrait["Footprint"]): ...


class Pad(ModuleInterface):
    def __init__(self) -> None:
        super().__init__()

        class _IFS(super().IFS()):
            net = Electrical()
            pcb = ModuleInterface()

        self.IFs = _IFS(self)


class Footprint(Module):
    def __init__(self) -> None:
        super().__init__()
