# This file is part of the faebryk project
# SPDX-License-Identifier: MIT


from faebryk.library.core import ComponentTrait
from faebryk.library.core import FootprintTrait


# Component Traits ------------------------------------------------------------
class has_kicad_ref(ComponentTrait):
    def get_ref() -> str:
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
    def get_kicad_footprint(self) -> str:
        raise NotImplementedError()


class has_kicad_manual_footprint(has_kicad_footprint.impl()):
    def __init__(self, str) -> None:
        super().__init__()
        self.str = str

    def get_kicad_footprint(self):
        return self.str


# -----------------------------------------------------------------------------
