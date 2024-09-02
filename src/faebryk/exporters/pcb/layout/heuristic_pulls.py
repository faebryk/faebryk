# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging

import faebryk.library._F as F
from faebryk.core.module import Module
from faebryk.core.node import Node
from faebryk.core.util import get_parent_of_type, get_parent_with_trait
from faebryk.exporters.pcb.layout.heuristic_decoupling import place_next_to
from faebryk.exporters.pcb.layout.layout import Layout
from faebryk.libs.util import NotNone, find

logger = logging.getLogger(__name__)


class LayoutHeuristicElectricalClosenessPullResistors(Layout):
    def apply(self, *node: Node):
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
            up, down = logic.get_trait(ElectricLogic.has_pulls).get_pulls()
            if n is up:
                level = logic.reference.hv
            elif n is down:
                level = logic.reference.lv
            else:
                assert False

            ic_side = find(
                n.get_children(direct_only=True, types=F.Electrical),
                lambda intf: not intf.is_connected_to(level) is not None,
            )

            parent = get_parent_with_trait(n, F.has_footprint, include_self=False)[0]
            assert isinstance(parent, Module)
            place_next_to(parent, ic_side, n, route=True)

    @staticmethod
    def find_module_candidates(node: Node):
        return node.get_children(
            direct_only=False,
            types=F.Resistor,
            f_filter=lambda c: get_parent_of_type(c, F.ElectricLogic) is not None,
        )

    @classmethod
    def add_to_all_suitable_modules(cls, node: Node):
        layout = cls()
        for c in cls.find_module_candidates(node):
            c.add_trait(F.has_pcb_layout_defined(layout))
