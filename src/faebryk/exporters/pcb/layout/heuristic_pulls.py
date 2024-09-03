# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging

import faebryk.library._F as F
from faebryk.core.node import Node
from faebryk.exporters.pcb.layout.heuristic_decoupling import Params, place_next_to
from faebryk.exporters.pcb.layout.layout import Layout
from faebryk.libs.util import NotNone

logger = logging.getLogger(__name__)


class LayoutHeuristicElectricalClosenessPullResistors(Layout):
    Parameters = Params

    def __init__(self, params: Params | None = None):
        super().__init__()
        self._params = params or Params()

    def apply(self, *node: Node):
        from faebryk.core.util import get_parent_of_type
        from faebryk.library.ElectricLogic import ElectricLogic
        from faebryk.library.Resistor import Resistor

        # Remove nodes that have a position defined
        node = tuple(
            n
            for n in node
            if not n.has_trait(F.has_pcb_position) and n.has_trait(F.has_footprint)
        )

        for n in node:
            assert isinstance(n, Resistor)
            logic = NotNone(get_parent_of_type(n, ElectricLogic))

            place_next_to(logic.signal, n, route=True, params=self._params)

    @staticmethod
    def find_module_candidates(node: Node):
        from faebryk.core.util import get_parent_of_type

        return node.get_children(
            direct_only=False,
            types=F.Resistor,
            f_filter=lambda c: get_parent_of_type(c, F.ElectricLogic) is not None,
        )

    @classmethod
    def add_to_all_suitable_modules(cls, node: Node, params: Params | None = None):
        layout = cls(params)
        for c in cls.find_module_candidates(node):
            c.add_trait(F.has_pcb_layout_defined(layout))
