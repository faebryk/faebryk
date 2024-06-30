# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging
from dataclasses import dataclass

from faebryk.core.core import (
    Module,
    Node,
)
from faebryk.core.util import get_node_tree
from faebryk.exporters.pcb.layout.layout import Layout
from faebryk.libs.util import find

logger = logging.getLogger(__name__)


@dataclass
class LayoutTypeHierarchy(Layout):
    @dataclass
    class Level:
        mod_type: type[Module]
        layout: Layout
        children_layout: Layout | None = None
        collective: bool = True

    layouts: list[Level]

    def apply(self, *node: Node):
        """
        Tip: Make sure at least one parent of node has an absolute position defined
        """
        for n in node:
            self._apply(n)

    def _apply(self, node: Node):
        tree = get_node_tree(node)
        direct_children = tree[node]

        # Find layout for the node
        try:
            level = find(self.layouts, lambda layout: isinstance(node, layout.mod_type))
        except KeyError:
            # node not in this level, descend to direct children nodes
            self.apply(*direct_children)
            return

        # Use node specific layout to apply
        level.layout.apply(node)

        # Recurse
        if not level.children_layout:
            return

        if level.collective:
            level.children_layout.apply(*direct_children)
        else:
            for child in direct_children:
                level.children_layout.apply(child)
