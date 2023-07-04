# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

from faebryk.core.core import Footprint
from faebryk.library.can_attach_via_pinmap_equal import can_attach_via_pinmap_equal
from faebryk.library.Electrical import Electrical
from faebryk.library.has_equal_pins_in_ifs import has_equal_pins_in_ifs
from faebryk.libs.util import times


class DIP(Footprint):
    def __init__(self, pin_cnt: int, spacing_mm: float, long_pads: bool) -> None:
        super().__init__()

        class _IFs(Footprint.IFS()):
            pins = times(pin_cnt, Electrical)

        self.IFs = _IFs(self)
        from faebryk.library.has_kicad_footprint_equal_ifs import (
            has_kicad_footprint_equal_ifs,
        )

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
