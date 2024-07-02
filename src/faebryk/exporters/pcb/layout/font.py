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
from faebryk.libs.geometry.basic import fill_poly_with_nodes_on_grid, transform_polygons

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

        assert bbox or char_dimensions, "Either bbox or char_dimensions must be given"
        # TODO
        # if not char_dimensions:
        #    char_dimensions = bbox[0] / len(text), bbox[1]
        if not char_dimensions:
            raise NotImplementedError()

        self.poly_glyphs = [
            # poly for letter in text for poly in self.font.letter_to_polygons(letter)
            self.font.letter_to_polygons(letter)
            for letter in text
        ]

        # Debugging
        if logger.isEnabledFor(logging.DEBUG):
            for i, polys in enumerate(self.poly_glyphs):
                logger.debug(f"Found {len(polys)} polygons for letter {text[i]}")
                for p in polys:
                    logger.debug(f"Polygon with {len(p.exterior.coords)} vertices")
                    logger.debug(f"Coords: {list(p.exterior.coords)}")

        # normalize
        max_dim = self.font.get_max_glyph_dimensions(text)
        self.poly_glyphs = transform_polygons(self.poly_glyphs, max_dim)

        # scale to the desired dimensions
        self.poly_glyphs = transform_polygons(
            self.poly_glyphs, (0, 0, 1 / char_dimensions[0], 1 / char_dimensions[1])
        )

        self.coords = []
        for i, polys in enumerate(self.poly_glyphs):
            # Debugging
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug(f"Processing letter {text[i]}")
                logger.debug(f"Found {len(polys)} polygons for letter {text[i]}")
                for p in polys:
                    logger.debug(f"Polygon with {len(p.exterior.coords)} vertices")
                    logger.debug(f"Coords: {list(p.exterior.coords)}")

            glyph_nodes = fill_poly_with_nodes_on_grid(
                polys=polys,
                grid_pitch=resolution,
                grid_offset=(
                    1 / resolution[0] / 2,
                    1 / resolution[1] / 2,
                ),
            )
            for node in glyph_nodes:
                self.coords.append(
                    (
                        node[0] + i * (char_dimensions[0] + kerning),
                        node[1],
                    )
                )
            logger.debug(f"Found {len(glyph_nodes)} nodes for letter {text[i]}")

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
