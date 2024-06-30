# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging

from faebryk.core.core import Module
from faebryk.core.util import get_node_tree, iter_tree_by_depth
from faebryk.library.has_pcb_layout import has_pcb_layout
from faebryk.library.has_pcb_position import has_pcb_position
from faebryk.library.has_pcb_position_defined import has_pcb_position_defined

logger = logging.getLogger(__name__)


def apply_layouts(app: Module):
    if not app.has_trait(has_pcb_position):
        app.add_trait(
            has_pcb_position_defined(
                has_pcb_position.Point((0, 0, 0, has_pcb_position.layer_type.NONE))
            )
        )

    tree = get_node_tree(app)
    for level in iter_tree_by_depth(tree):
        for n in level:
            if n.has_trait(has_pcb_layout):
                n.get_trait(has_pcb_layout).apply()
