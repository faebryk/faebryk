import logging

from faebryk.library.core import Component
from faebryk.library.library.electronic.interface.differential_pair import (
    DifferentialPair,
)
from faebryk.library.trait_impl.component import (
    has_defined_footprint_pinmap,
    has_defined_type_description,
)
from faebryk.library.util import times

logger = logging.getLogger("RJ45")


class RJ45_Receptacle(Component):
    def __init__(self) -> None:
        super().__init__()

        # interfaces
        class _IFs(Component.InterfacesCls()):
            twisted_pairs = times(4, DifferentialPair)

        self.IFs = _IFs(self)

        self.add_trait(
            has_defined_footprint_pinmap(
                {
                    "1": self.IFs.twisted_pairs[0].IFs.p,
                    "2": self.IFs.twisted_pairs[0].IFs.n,
                    "3": self.IFs.twisted_pairs[1].IFs.p,
                    "4": self.IFs.twisted_pairs[1].IFs.n,
                    "5": self.IFs.twisted_pairs[2].IFs.p,
                    "6": self.IFs.twisted_pairs[2].IFs.n,
                    "7": self.IFs.twisted_pairs[3].IFs.p,
                    "8": self.IFs.twisted_pairs[3].IFs.n,
                }
            )
        )
        self.add_trait(has_defined_type_description("x"))
