# This file is part of the faebryk project
# SPDX-License-Identifier: MIT


from abc import abstractmethod
from typing import Dict

from faebryk.library.core import Footprint, FootprintTrait, NodeTrait
from faebryk.library.library.footprints import can_attach_via_pinmap_pinlist
from faebryk.library.library.interfaces import Electrical
from faebryk.library.util import times


# Footprints ------------------------------------------------------------------
class KicadFootprint(Footprint):
    def __init__(self, kicad_identifier: str, pin_names: list[str]) -> None:
        super().__init__()

        class _IFS(Footprint.IFS()):
            pins = times(len(pin_names), Electrical)

        self.IFs = _IFS(self)

        self.add_trait(
            can_attach_via_pinmap_pinlist(
                {pin_name: self.IFs.pins[i] for i, pin_name in enumerate(pin_names)}
            )
        )

        self.add_trait(
            has_kicad_manual_footprint(
                kicad_identifier,
                {self.IFs.pins[i]: pin_name for i, pin_name in enumerate(pin_names)},
            )
        )

    @classmethod
    def with_simple_names(cls, kicad_identifier: str, pin_cnt: int):
        return cls(kicad_identifier, [str(i + 1) for i in range(pin_cnt)])


# -----------------------------------------------------------------------------


# Component Traits ------------------------------------------------------------
class has_kicad_ref(NodeTrait):
    def get_ref(self) -> str:
        raise NotImplementedError()


class has_defined_kicad_ref(has_kicad_ref.impl()):
    def __init__(self, ref: str) -> None:
        super().__init__()
        self.ref = ref

    def get_ref(self) -> str:
        return self.ref


# -----------------------------------------------------------------------------


# Footprint Traits ------------------------------------------------------------
class has_kicad_footprint(FootprintTrait):
    @abstractmethod
    def get_kicad_footprint(self) -> str:
        ...

    @abstractmethod
    def get_pin_names(self) -> Dict[Electrical, str]:
        ...


class has_kicad_manual_footprint(has_kicad_footprint.impl()):
    def __init__(self, str, pinmap: Dict[Electrical, str]) -> None:
        super().__init__()
        self.str = str
        self.pinmap = pinmap

    def get_kicad_footprint(self):
        return self.str

    def get_pin_names(self):
        return self.pinmap


class has_kicad_footprint_equal_ifs(has_kicad_footprint.impl()):
    def get_pin_names(self):
        from faebryk.library.library.footprints import has_equal_pins

        return self.get_obj().get_trait(has_equal_pins).get_pin_map()


class has_kicad_footprint_equal_ifs_defined(has_kicad_footprint_equal_ifs):
    def __init__(self, str) -> None:
        super().__init__()
        self.str = str

    def get_kicad_footprint(self):
        return self.str


# -----------------------------------------------------------------------------
