import logging

from faebryk.library.core import Component
from faebryk.library.library.electronic.interface.differential_pair import (
    DifferentialPair,
)
from faebryk.library.library.interfaces import Electrical
from faebryk.library.trait_impl.component import (
    has_defined_footprint_pinmap,
    has_defined_type_description,
)
from faebryk.library.util import times

logger = logging.getLogger("USB type-C")


class USB_Type_C_Receptacle_24_pin(Component):
    def __init__(self) -> None:
        super().__init__()

        # interfaces
        class _IFs(Component.InterfacesCls()):
            cc1 = Electrical()
            cc2 = Electrical()
            sbu1 = Electrical()
            sbu2 = Electrical()
            shield = Electrical()
            # power
            gnd = times(4, Electrical)
            vbus = times(4, Electrical)
            # diffpairs: p, n
            rx1 = DifferentialPair()
            rx2 = DifferentialPair()
            tx1 = DifferentialPair()
            tx2 = DifferentialPair()
            d1 = DifferentialPair()
            d2 = DifferentialPair()

        self.IFs = _IFs(self)

        self.add_trait(
            has_defined_footprint_pinmap(
                {
                    "A1": self.IFs.gnd[0],
                    "A2": self.IFs.tx1.IFs.p,
                    "A3": self.IFs.tx1.IFs.n,
                    "A4": self.IFs.vbus[0],
                    "A5": self.IFs.cc1,
                    "A6": self.IFs.d1.IFs.p,
                    "A7": self.IFs.d1.IFs.n,
                    "A8": self.IFs.sbu1,
                    "A9": self.IFs.vbus[1],
                    "A10": self.IFs.rx2.IFs.n,
                    "A11": self.IFs.rx2.IFs.p,
                    "A12": self.IFs.gnd[1],
                    "B1": self.IFs.gnd[2],
                    "B2": self.IFs.tx2.IFs.p,
                    "B3": self.IFs.tx2.IFs.n,
                    "B4": self.IFs.vbus[2],
                    "B5": self.IFs.cc2,
                    "B6": self.IFs.d2.IFs.p,
                    "B7": self.IFs.d2.IFs.n,
                    "B8": self.IFs.sbu2,
                    "B9": self.IFs.vbus[3],
                    "B10": self.IFs.rx1.IFs.n,
                    "B11": self.IFs.rx1.IFs.p,
                    "B12": self.IFs.gnd[3],
                    "0": self.IFs.shield,
                }
            )
        )

        self.add_trait(has_defined_type_description("x"))
