# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging

logger = logging.getLogger("library")

from faebryk.library.kicad import has_kicad_footprint
from faebryk.library.core import Footprint
from faebryk.library.traits import *
from enum import Enum

class DIP(Footprint):
    def __init__(self, pin_cnt: int, spacing_mm: int, long_pads: bool) -> None:
        super().__init__()

        class _has_kicad_footprint(has_kicad_footprint):
            @staticmethod
            def get_kicad_footprint() -> str:
                return \
                    "Package_DIP:DIP-{leads}_W{spacing:.2f}mm{longpads}".format(
                        leads=pin_cnt,
                        spacing=spacing_mm,
                        longpads="_LongPads" if long_pads else ""
                    )

        self.add_trait(_has_kicad_footprint())

class SMDTwoPin(Footprint):
    class Type(Enum):
        _01005 = 0
        _0201  = 1
        _0402  = 2
        _0603  = 3
        _0805  = 4
        _1206  = 5
        _1210  = 6
        _1218  = 7
        _2010  = 8
        _2512  = 9

    def __init__(self, type: Type) -> None:
        super().__init__()

        class _has_kicad_footprint(has_kicad_footprint):
            @staticmethod
            def get_kicad_footprint() -> str:
                table = {
                    self.Type._01005: "0402",
                    self.Type._0201:  "0603",
                    self.Type._0402:  "1005",
                    self.Type._0603:  "1005",
                    self.Type._0805:  "2012",
                    self.Type._1206:  "3216",
                    self.Type._1210:  "3225",
                    self.Type._1218:  "3246",
                    self.Type._2010:  "5025",
                    self.Type._2512:  "6332",
                }

                return \
                    "Resistor_SMD:R_{imperial}_{metric}Metric".format(
                        imperial=type.name[1:],
                        metric=table[type]
                    )

        self.add_trait(_has_kicad_footprint())
