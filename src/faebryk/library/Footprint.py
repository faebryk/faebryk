# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

from abc import abstractmethod
from typing import Generic, TypeVar

from faebryk.core.core import (
    Module,
    ModuleInterface,
    ModuleInterfaceTrait,
    Node,
    _ModuleTrait,
)
from faebryk.core.util import get_parent_of_type
from faebryk.library.Electrical import Electrical

TF = TypeVar("TF", bound="Footprint")


class _FootprintTrait(Generic[TF], _ModuleTrait[TF]): ...


class FootprintTrait(_FootprintTrait["Footprint"]): ...


class has_linked_pad(ModuleInterfaceTrait):
    @abstractmethod
    def get_pad(self) -> "Pad": ...


class has_linked_pad_defined(has_linked_pad.impl()):
    def __init__(self, pad: "Pad") -> None:
        super().__init__()
        self.pad = pad

    def get_pad(self) -> "Pad":
        return self.pad


class Pad(ModuleInterface):
    def __init__(self) -> None:
        super().__init__()

        class _IFS(super().IFS()):
            net = Electrical()
            pcb = ModuleInterface()

        self.IFs = _IFS(self)

    def attach(self, intf: Electrical):
        self.IFs.net.connect(intf)
        intf.add_trait(has_linked_pad_defined(self))

    @staticmethod
    def find_pad_for_intf_with_parent_that_has_footprint_unique(
        intf: ModuleInterface,
    ) -> "Pad":
        pads = Pad.find_pad_for_intf_with_parent_that_has_footprint(intf)
        if len(pads) != 1:
            raise ValueError
        return next(iter(pads))

    @staticmethod
    def find_pad_for_intf_with_parent_that_has_footprint(
        intf: ModuleInterface,
    ) -> list["Pad"]:
        # This only finds directly attached pads
        # -> misses from parents / children nodes
        if intf.has_trait(has_linked_pad):
            return [intf.get_trait(has_linked_pad).get_pad()]

        # This is a bit slower, but finds them all
        _, footprint = Footprint.get_footprint_of_parent(intf)
        pads = [
            pad
            for pad in footprint.IFs.get_all()
            if isinstance(pad, Pad) and pad.IFs.net.is_connected_to(intf) is not None
        ]
        return pads

    def get_fp(self) -> "Footprint":
        fp = get_parent_of_type(self, Footprint)
        assert fp
        return fp


class Footprint(Module):
    def __init__(self) -> None:
        super().__init__()

    @staticmethod
    def get_footprint_of_parent(
        intf: ModuleInterface,
    ) -> "tuple[Node, Footprint]":
        from faebryk.core.util import get_parent_with_trait
        from faebryk.library.has_footprint import has_footprint

        parent, trait = get_parent_with_trait(intf, has_footprint)
        return parent, trait.get_footprint()
