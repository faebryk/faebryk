# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging
logger = logging.getLogger("library")

from faebryk.library.core import FootprintTrait

class has_kicad_footprint(FootprintTrait):
    def get_kicad_footprint(self) -> str:
        raise NotImplementedError()
    
class has_kicad_manual_footprint(has_kicad_footprint):
    def __init__(self, str) -> None:
        super().__init__()
        self.str = str

    def get_kicad_footprint(self):
        return self.str
    