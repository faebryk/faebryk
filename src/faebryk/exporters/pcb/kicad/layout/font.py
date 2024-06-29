# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging
from math import inf
from pathlib import Path

import numpy as np
from faebryk.core.core import Node
from faebryk.exporters.pcb.kicad.layout.layout import Layout
from faebryk.library.has_pcb_position import has_pcb_position
from faebryk.library.has_pcb_position_defined_relative_to_parent import (
    has_pcb_position_defined_relative_to_parent,
)
from fontTools.pens.boundsPen import BoundsPen
from fontTools.pens.recordingPen import RecordingPen
from fontTools.ttLib import TTFont
from shapely import Point, Polygon, transform

logger = logging.getLogger(__name__)


class FontLayout(Layout):
    def __init__(
        self,
        ttf: Path,
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

        assert bbox or char_dimensions, "Either bbox or char_dimensions must be given"
        # TODO
        # if not char_dimensions:
        #    char_dimensions = bbox[0] / len(text), bbox[1]
        if not char_dimensions:
            raise NotImplementedError()

        self.poly_glyphs = []
        for letter in text:
            self.poly_glyphs.append(self._ttf_letter_to_polygons(ttf, letter))

        for i, polys in enumerate(self.poly_glyphs):
            logger.debug(f"Found {len(polys)} polygons for letter {text[i]}")
            for p in polys:
                logger.debug(f"Polygon with {len(p.exterior.coords)} vertices")
                logger.debug(f"Coords: {list(p.exterior.coords)}")

        # normalize
        font = TTFont(ttf)
        max_dim = self._get_max_glyph_dimensions(font, text)
        self.poly_glyphs = self._transform_polygons(self.poly_glyphs, max_dim)

        # scale to the desired dimensions
        self.poly_glyphs = self._transform_polygons(
            self.poly_glyphs, (0, 0, 1 / char_dimensions[0], 1 / char_dimensions[1])
        )

        self.coords = []
        for i, polys in enumerate(self.poly_glyphs):
            logger.debug(f"Processing letter {text[i]}")
            logger.debug(f"Found {len(polys)} polygons for letter {text[i]}")
            for p in polys:
                logger.debug(f"Polygon with {len(p.exterior.coords)} vertices")
                logger.debug(f"Coords: {list(p.exterior.coords)}")
            glyph_nodes = self._fill_poly_with_nodes_on_grid(
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
                    (coord[0], -coord[1], 0, has_pcb_position.layer_type.NONE)
                )
            )

    def _get_max_glyph_dimensions(
        self, font, text: str | None = None
    ) -> tuple[float, float, float, float]:
        """
        Get the maximum dimensions of all glyphs combined in a font
        """
        glyphset = font.getGlyphSet()
        bp = BoundsPen(glyphset)

        max_dim = (inf, inf, -inf, -inf)
        for glyph_name in glyphset.keys() if text is None else set(text):
            glyphset[glyph_name].draw(bp)

            if not bp.bounds:
                continue

            max_dim = (
                min(max_dim[0], bp.bounds[0]),
                min(max_dim[1], bp.bounds[1]),
                max(max_dim[2], bp.bounds[2]),
                max(max_dim[3], bp.bounds[3]),
            )

        return max_dim

    def _transform_polygons(
        self, polys: list[Polygon], dim: tuple[float, float, float, float]
    ) -> list[Polygon]:
        """
        Transform a list of polygons using a transformation matrix

        :param polys: The polygons to transform
        :param dim: The transformation matrix (x_min, y_min, x_max, y_max)
        """

        scale_x = 1 / (dim[2] - dim[0])
        scale_y = 1 / (dim[3] - dim[1])
        offset_x = -dim[0]
        offset_y = -dim[1]

        scaled_polys = []
        for poly in polys:
            scaled_polys.append(
                transform(
                    poly, lambda x: (x + [offset_x, offset_y]) * [scale_x, scale_y]
                )
            )

        return scaled_polys

    def _ttf_letter_to_polygons(self, ttf_path: Path, letter: str) -> list[Polygon]:
        """
        Extract the polygons of a single letter from a ttf font file

        :param ttf_path: Path to the ttf font file
        :param letter: The letter to extract
        :return: A list of polygons that represent the letter
        """
        font = TTFont(ttf_path)
        cmap = font.getBestCmap()
        glyph_set = font.getGlyphSet()
        glyph = glyph_set[cmap[ord(letter)]]
        contours = self._extract_contours(glyph)

        polys = []
        for contour in contours:
            polys.append(Polygon(contour))

        return polys

    def _extract_contours(self, glyph) -> list[list[tuple[float, float]]]:
        """
        Extract the contours of a glyph

        :param glyph: The glyph to extract the contours from
        :return: A list of contours, each represented by a list of coordinates
        """
        contours = []
        current_contour = []
        pen = RecordingPen()
        glyph.draw(pen)
        trace = pen.value
        for flag, coords in trace:
            if flag == "lineTo":  # On-curve point
                current_contour.append(coords[0])
            if flag == "moveTo":  # Move to a new contour
                current_contour = [coords[0]]
            if flag == "closePath":  # Close the current contour
                current_contour.append(current_contour[0])
                contours.append(current_contour)
        return contours

    def _fill_poly_with_nodes_on_grid(
        self,
        polys: list[Polygon],
        grid_pitch: tuple[float, float],
        grid_offset: tuple[float, float],
    ) -> list[tuple[float, float]]:
        """
        Get a list of points on a grid that are inside a polygon

        :param polys: The polygons to check
        :param grid_pitch: The pitch of the grid (x, y)
        :param grid_offset: The offset of the grid (x, y)
        :return: A list of points that are inside the polygons
        """

        pixels = []
        min_x, min_y, max_x, max_y = (inf, inf, -inf, -inf)
        for b in [(p.bounds) for p in polys]:
            min_x = min(min_x, b[0])
            min_y = min(min_y, b[1])
            max_x = max(max_x, b[2])
            max_y = max(max_y, b[3])

        for poly in polys:
            for x in np.arange(min_x, max_x, grid_pitch[0]):
                x += grid_offset[0]
                for y in np.arange(min_x, max_y, grid_pitch[1]):
                    y += grid_offset[1]
                    if poly.contains(Point(x, y)):
                        pixels.append((x, y))

        return pixels
