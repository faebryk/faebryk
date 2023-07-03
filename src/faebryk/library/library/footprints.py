# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging
from abc import abstractmethod
from typing import Dict

from faebryk.library.core import Footprint, FootprintTrait, ModuleInterface, ModuleTrait
from faebryk.library.library.interfaces import Electrical
from faebryk.library.trait_impl.component import has_defined_footprint
from faebryk.libs.util import times

logger = logging.getLogger(__name__)

from enum import Enum


# TODO move file --------------------------------------------------------------
class can_attach_via_pinmap(FootprintTrait):
    @abstractmethod
    def attach(self, pinmap: Dict[str, Electrical]):
        ...


class can_attach_via_pinmap_pinlist(can_attach_via_pinmap.impl()):
    def __init__(self, pin_list: Dict[str, Electrical]) -> None:
        super().__init__()
        self.pin_list = pin_list

    def attach(self, pinmap: Dict[str, Electrical]):
        for no, intf in pinmap.items():
            self.pin_list[no].connect(intf)


class can_attach_via_pinmap_equal(can_attach_via_pinmap.impl()):
    def attach(self, pinmap: Dict[str, Electrical]):
        pin_list = {
            v: k
            for k, v in self.get_obj().get_trait(has_equal_pins).get_pin_map().items()
        }
        for no, intf in pinmap.items():
            pin_list[no].connect(intf)


class can_attach_to_footprint(ModuleTrait):
    @abstractmethod
    def attach(self, footprint: Footprint):
        ...


class can_attach_to_footprint_symmetrically(can_attach_to_footprint.impl()):
    def attach(self, footprint: Footprint):
        self.get_obj().add_trait(has_defined_footprint(footprint))

        # connect interfaces footprint <-> component
        for i, j in zip(
            footprint.IFs.get_all(),
            self.get_obj().IFs.get_all(),
        ):
            # TODO should be already encoded into IFS
            assert isinstance(i, ModuleInterface)
            assert isinstance(j, ModuleInterface)
            assert type(i) == type(j)
            i.connect(j)


class can_attach_to_footprint_via_pinmap(can_attach_to_footprint.impl()):
    def __init__(self, pinmap: Dict[str, Electrical]) -> None:
        super().__init__()
        self.pinmap = pinmap

    def attach(self, footprint: Footprint):
        self.get_obj().add_trait(has_defined_footprint(footprint))

        footprint.get_trait(can_attach_via_pinmap).attach(self.pinmap)


class has_equal_pins(FootprintTrait):
    @abstractmethod
    def get_pin_map(self) -> dict[Electrical, str]:
        ...


class has_equal_pins_in_ifs(has_equal_pins.impl()):
    def get_pin_map(self):
        return {p: str(i + 1) for i, p in enumerate(self.get_obj().IFs.get_all())}


# -----------------------------------------------------------------------------


class DIP(Footprint):
    def __init__(self, pin_cnt: int, spacing_mm: float, long_pads: bool) -> None:
        super().__init__()

        class _IFs(Footprint.IFS()):
            pins = times(pin_cnt, Electrical)

        self.IFs = _IFs(self)

        from faebryk.library.kicad import has_kicad_footprint_equal_ifs

        class _has_kicad_footprint(has_kicad_footprint_equal_ifs):
            @staticmethod
            def get_kicad_footprint() -> str:
                return "Package_DIP:DIP-{leads}_W{spacing:.2f}mm{longpads}".format(
                    leads=pin_cnt,
                    spacing=spacing_mm,
                    longpads="_LongPads" if long_pads else "",
                )

        self.add_trait(_has_kicad_footprint())
        self.add_trait(has_equal_pins_in_ifs())
        self.add_trait(can_attach_via_pinmap_equal())


class QFN(Footprint):
    def __init__(
        self,
        pin_cnt: int,
        exposed_thermal_pad_cnt: int,
        size_xy_mm: tuple[float, float],
        pitch_mm: float,
        exposed_thermal_pad_dimensions_mm: tuple[float, float],
        has_thermal_vias: bool,
    ) -> None:
        super().__init__()

        class _IFs(Footprint.IFS()):
            pins = times(pin_cnt, Electrical)

        self.IFs = _IFs(self)

        # Constraints
        assert exposed_thermal_pad_cnt > 0 or not has_thermal_vias
        assert (
            exposed_thermal_pad_dimensions_mm[0] < size_xy_mm[0]
            and exposed_thermal_pad_dimensions_mm[1] < size_xy_mm[1]
        )

        from faebryk.library.kicad import has_kicad_footprint_equal_ifs

        class _has_kicad_footprint(has_kicad_footprint_equal_ifs):
            @staticmethod
            def get_kicad_footprint() -> str:
                # example: QFN-16-1EP_4x4mm_P0.5mm_EP2.45x2.45mm_ThermalVias
                return "Package_DFN_QFN:QFN-{leads}-{ep}EP_{size_x}x{size_y}mm_P{pitch}mm_EP{ep_x}x{ep_y}mm{vias}".format(
                    leads=pin_cnt,
                    ep=exposed_thermal_pad_cnt,
                    size_x=size_xy_mm[0],
                    size_y=size_xy_mm[1],
                    pitch=pitch_mm,
                    ep_x=exposed_thermal_pad_dimensions_mm[0],
                    ep_y=exposed_thermal_pad_dimensions_mm[1],
                    vias="_ThermalVias" if has_thermal_vias else "",
                )

        self.add_trait(_has_kicad_footprint())
        self.add_trait(has_equal_pins_in_ifs())
        self.add_trait(can_attach_via_pinmap_equal())


class SMDTwoPin(Footprint):
    class Type(Enum):
        _01005 = 0
        _0201 = 1
        _0402 = 2
        _0603 = 3
        _0805 = 4
        _1206 = 5
        _1210 = 6
        _1218 = 7
        _2010 = 8
        _2512 = 9

    def __init__(self, type: Type) -> None:
        super().__init__()

        class _IFs(Footprint.IFS()):
            pins = times(2, Electrical)

        self.IFs = _IFs(self)

        from faebryk.library.kicad import has_kicad_footprint_equal_ifs

        class _has_kicad_footprint(has_kicad_footprint_equal_ifs):
            @staticmethod
            def get_kicad_footprint() -> str:
                table = {
                    self.Type._01005: "0402",
                    self.Type._0201: "0603",
                    self.Type._0402: "1005",
                    self.Type._0603: "1005",
                    self.Type._0805: "2012",
                    self.Type._1206: "3216",
                    self.Type._1210: "3225",
                    self.Type._1218: "3246",
                    self.Type._2010: "5025",
                    self.Type._2512: "6332",
                }

                return "Resistor_SMD:R_{imperial}_{metric}Metric".format(
                    imperial=type.name[1:], metric=table[type]
                )

        self.add_trait(_has_kicad_footprint())
        self.add_trait(has_equal_pins_in_ifs())
        self.add_trait(can_attach_via_pinmap_equal())
