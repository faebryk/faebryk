import logging
from typing import Callable

import faebryk.library._F as F
import faebryk.libs.picker.jlcpcb.picker_lib as P
from faebryk.core.core import Module
from faebryk.libs.picker.picker import has_part_picked

logger = logging.getLogger(__name__)


class JLCPCBPicker(F.has_multi_picker.Picker):
    def __init__(self, picker: Callable[[Module, int], None]):
        self.picker = picker

    def pick(self, module: Module, qty: int = 1) -> None:
        assert not module.has_trait(has_part_picked)
        self.picker(module, qty)

    def __repr__(self):
        return f"<{self.__class__.__name__} ({self.picker.__name__})>"


def add_jlcpcb_pickers(module: Module, base_prio: int = 0) -> None:
    # Generic pickers

    prio = base_prio
    F.has_multi_picker.add_to_module(
        module,
        prio,
        JLCPCBPicker(P.find_lcsc_part),
    )
    F.has_multi_picker.add_to_module(
        module,
        prio,
        JLCPCBPicker(P.find_manufacturer_part),
    )

    # Type specific pickers
    prio = base_prio + 1

    picker_types = [k for k in P.TYPE_SPECIFIC_LOOKUP if isinstance(module, k)]
    # sort by most specific first
    picker_types.sort(key=lambda x: len(x.__mro__), reverse=True)

    for i, k in enumerate(picker_types):
        v = P.TYPE_SPECIFIC_LOOKUP[k]
        F.has_multi_picker.add_to_module(
            module,
            # most specific first
            prio + i,
            JLCPCBPicker(v),
        )
