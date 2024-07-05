# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging

from faebryk.core.core import Node
from faebryk.exporters.pcb.layout.layout import Layout
from faebryk.library.has_pcb_position import has_pcb_position
from faebryk.library.has_pcb_position_defined_relative_to_parent import (
    has_pcb_position_defined_relative_to_parent,
)
from faebryk.libs.font import Font
from faebryk.libs.geometry.basic import get_distributed_points_in_polygon

logger = logging.getLogger(__name__)


class FontLayout(Layout):
    def __init__(
        self,
        font: Font,
        text: str,
        resolution: tuple[float, float],
        bbox: tuple[float, float] | None = None,
        char_dimensions: tuple[float, float] | None = None,
        kerning: float = 1,
    ) -> None:
        """
        Map a text string with a given font to a grid with a given resolution and map
        a node on each node of the grid that is inside the string.

        :param ttf: Path to the ttf font file
        :param text: Text to render
        :param char_dimensions: Bounding box of a single character (x, y) in mm
        :param resolution: Resolution (x, y) in nodes/mm
        :param kerning: Distance between characters, relative to the resolution of a
        single character in mm
        """
        super().__init__()

        self.font = font

        polys = font.string_to_polygons(text, font_size=30)

        # set grid offset to half a grid pitch to center the nodes
        grid_offset = (1 / resolution[0] / 2, 1 / resolution[1] / 2)
        grid_pitch = (1 / resolution[0], 1 / resolution[1])

        logger.debug(f"Grid pitch: {grid_pitch}")
        logger.debug(f"Grid offset: {grid_offset}")

        nodes = []
        for p in polys:
            nodes.extend(get_distributed_points_in_polygon ( polygon=p, density=0.1) )

        self.coords = [(n.x, n.y) for n in nodes]

        # Move down because the font has the origin in the bottom left while KiCad has
        # it in the top left
        self.coords = [(c[0], -c[1]) for c in self.coords]

    def get_count(self) -> int:
        """
        Get the number of nodes that fit in the font
        """
        return len(self.coords)

    def apply(self, *nodes_to_distribute: Node) -> None:
        """
        Apply the PCB positions to all nodes that are inside the font
        """
        if len(nodes_to_distribute) != len(self.coords):
            logger.warning(
                f"Number of nodes to distribute ({len(nodes_to_distribute)})"
                " does not match"
                f" the number of coordinates ({len(self.coords)})"
            )

        for coord, node in zip(self.coords, nodes_to_distribute):
            node.add_trait(
                has_pcb_position_defined_relative_to_parent(
                    (
                        coord[0],
                        # TODO mirrored Y-axis bug
                        -coord[1],
                        0,
                        has_pcb_position.layer_type.NONE,
                    )
                )
            )

    def __hash__(self) -> int:
        return hash(id(self))
