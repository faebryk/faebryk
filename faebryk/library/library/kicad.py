# This file is part of the faebryk project
# SPDX-License-Identifier: MIT


#class KicadLibraryFootprint(Footprint):
#    def __init__(self, kicad_lib: kicadlib, library_identifier: str) -> None:
#        super().__init__()
#
#        #TODO check in lib
#
#        self.add_trait(has_kicad_footprint(library_identifier))

from faebryk.library.core import ComponentTrait


# Component Traits ------------------------------------------------------------
class has_kicad_ref(ComponentTrait):
    def get_ref() -> str:
        raise NotImplementedError()

class has_defined_kicad_ref(has_kicad_ref):
    def __init__(self, ref: str) -> None:
        super().__init__()
        self.ref = ref

    def get_ref(self) -> str:
        return self.ref

# -----------------------------------------------------------------------------