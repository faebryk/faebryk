# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging
from math import inf
from pathlib import Path

import freetype
import matplotlib.pyplot as plt
from faebryk.libs.geometry.basic import (
    flatten_polygons,
    get_distributed_points_in_polygon,
    transform_polygon,
)
from fontTools.pens.boundsPen import BoundsPen
from fontTools.pens.recordingPen import RecordingPen
from fontTools.ttLib import TTFont
from shapely import Point, Polygon

logger = logging.getLogger(__name__)


class Font:
    def __init__(self, ttf: Path):
        super().__init__()

        self.path = ttf
        self.font = TTFont(ttf)

    def get_max_glyph_dimensions(
        self, text: str | None = None
    ) -> tuple[float, float, float, float]:
        """
        Get the maximum dimensions of all glyphs combined in a font
        """
        glyphset = self.font.getGlyphSet()
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

    def letter_to_polygons(self, letter: str) -> list[Polygon]:
        """
        Extract the polygons of a single letter from a ttf font file

        :param ttf_path: Path to the ttf font file
        :param letter: The letter to extract
        :return: A list of polygons that represent the letter
        """
        font = self.font
        cmap = font.getBestCmap()
        glyph_set = font.getGlyphSet()
        glyph = glyph_set[cmap[ord(letter)]]
        contours = Font.extract_contours(glyph)

        polys = []
        for contour in contours:
            polys.append(Polygon(contour))

        return polys

    def string_to_polygons(
        self,
        string: str,
        font_size: int,
        bbox: tuple[int, int] | None = None,
        wrap: bool = False,
        scale_to_fit: bool = False,
    ) -> list[Polygon]:
        """
        Render the polygons of a string from a ttf font file

        :param ttf_path: Path to the ttf font file
        :param string: The string to extract
        :param font_size: The font size in points
        :param bbox: The bounding box to fit the text in, in points
        :param wrap: Wrap the text to fit the bounding box
        :param scale_to_fit: Scale the text to fit the bounding box
        :return: A list of polygons that represent the string
        """

        if wrap and not bbox:
            raise ValueError("Bounding box must be given when wrapping text")

        if scale_to_fit and not bbox:
            raise ValueError("Bounding box must be given when fitting text")

        # TODO: use bezier control points in outline.tags

        face = freetype.Face(str(self.path))
        polys = []
        offset = Point(0, 0)
        if scale_to_fit:
            raise NotImplementedError("Scaling to fit is not yet implemented")

        scale = font_size / face.units_per_EM
        for char in string:
            face.load_char(char)

            if bbox:
                if offset.x + face.glyph.advance.x > bbox[0] / scale:
                    if not wrap:
                        break
                    offset = Point(0, offset.y + face.glyph.advance.y)
                    if offset.y > bbox[1] / scale:
                        break

            points = face.glyph.outline.points
            contours = face.glyph.outline.contours

            for contour in contours:
                if not points:
                    break
                contour_points = [Point(p) for p in points[: contour + 1]]
                contour_points.append(contour_points[0])
                points = points[contour + 1 :]
                contour_points = [
                    Point(p.x + offset.x, p.y + offset.y) for p in contour_points
                ]
                polys.append(Polygon(contour_points))

            offset = Point(offset.x + face.glyph.advance.x, offset.y)

            if not wrap or not bbox:
                continue

            if offset.x > bbox[0]:
                offset = Point(0, offset.y + face.glyph.advance.y)
                if offset.y > bbox[1]:
                    break

        # for zone in polys:
        #    contour_points = list(zone.exterior.coords)
        #    plt.plot(*zip(*contour_points), marker="o")

        # plt.axis("equal")
        # plt.show()

        polys = flatten_polygons(polys)
        polys = [transform_polygon(p, scale=scale, offset=(0, 0)) for p in polys]

        # points = []
        # for poly in polys:
        #     points.extend(get_distributed_points_in_polygon(poly, 0.1))

        # exlcude_poly = Polygon(
        #     [
        #         (0, 5),
        #         (100, 5),
        #         (100, 10),
        #         (0, 10),
        #         (0, 5),
        #     ]
        # )
        # polys = [poly.difference(exlcude_poly) for poly in polys]

        # for zone in polys:
        #     contour_points = list(zone.exterior.coords)
        #     plt.plot(*zip(*contour_points), marker="o")

        # points = [(p.x, p.y) for p in points]
        # plt.plot(
        #     *zip(*points),
        #     marker="x",
        #     linestyle="None",
        # )

        # plt.axis("equal")
        # plt.show()

        # Invert the y-axis
        polys = [
            Polygon([(p[0], -p[1] + font_size) for p in polygon.exterior.coords])
            for polygon in polys
        ]

        return polys

    @staticmethod
    def extract_contours(glyph) -> list[list[tuple[float, float]]]:
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
