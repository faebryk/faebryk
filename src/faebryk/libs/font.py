# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging
from pathlib import Path

import freetype
import numpy as np
from faebryk.libs.geometry.basic import (
    flatten_polygons,
    get_point_on_bezier_curve,
    transform_polygon,
)
from shapely import Point, Polygon

logger = logging.getLogger(__name__)


class Font:
    def __init__(self, ttf: Path):
        super().__init__()

        self.path = ttf

    def string_to_polygons(
        self,
        string: str,
        font_size: float,
        bbox: tuple[float, float] | None = None,
        wrap: bool = False,
        scale_to_fit: bool = False,
        resolution: int = 10,
    ) -> list[Polygon]:
        """
        Render the polygons of a string from a ttf font file

        :param ttf_path: Path to the ttf font file
        :param string: The string to extract
        :param font_size: The font size in points
        :param bbox: The bounding box to fit the text in, in points
        :param wrap: Wrap the text to fit the bounding box
        :param scale_to_fit: Scale the text to fit the bounding box
        :param resolution: The resolution of the bezier curves
        :return: A list of polygons that represent the string
        """

        if wrap and not bbox:
            raise ValueError("Bounding box must be given when wrapping text")

        if scale_to_fit and not bbox:
            raise ValueError("Bounding box must be given when fitting text")

        if wrap and scale_to_fit:
            raise NotImplementedError("Cannot wrap and scale to fit at the same time")

        # TODO: use bezier control points in outline.tags

        face = freetype.Face(str(self.path))
        polygons = []

        if scale_to_fit:
            font_size = 1

        text_size = Point(0, 0)

        scale = font_size / face.units_per_EM
        for i, line in enumerate(reversed(string.split("\\n"))):
            offset = Point(0, i * face.units_per_EM)

            for char in line:
                face.load_char(char)

                if bbox and not scale_to_fit:
                    if offset.x + face.glyph.advance.x > bbox[0] / scale:
                        if not wrap:
                            break
                        offset = Point(0, offset.y + face.glyph.advance.y)
                        if offset.y > bbox[1] / scale:
                            break

                points = face.glyph.outline.points
                tags = face.glyph.outline.tags
                contours = face.glyph.outline.contours

                start = 0

                ts = np.linspace(0, 1, resolution)

                for contour in contours:
                    contour_points = []
                    point_info = list(
                        zip(points[start : contour + 1], tags[start : contour + 1])
                    )
                    point_info.append(point_info[0])
                    i = 0
                    while i < len(point_info):
                        # find segment of points that are off curve
                        segment = [point_info[i][0]]
                        i += 1
                        for j in range(i, len(point_info)):
                            point, tag = point_info[j]
                            segment.append(point)
                            if tag & 1:
                                i = j
                                break

                        contour_points.extend(
                            [
                                Point(
                                    get_point_on_bezier_curve(
                                        [np.array(s) for s in segment], ts
                                    )
                                )
                                for ts in ts
                            ]
                        )

                    # apply the offset
                    contour_points = [
                        Point(p.x + offset.x, p.y + offset.y) for p in contour_points
                    ]
                    polygons.append(Polygon(contour_points))

                    start = contour + 1

                offset = Point(offset.x + face.glyph.advance.x, offset.y)

                if not wrap or not bbox:
                    continue

                if offset.x > bbox[0]:
                    offset = Point(0, offset.y + face.glyph.advance.y)
                    if offset.y > bbox[1]:
                        logger.warning("Text does not fit in bounding box")
                        break

        bounds = [p.bounds for p in polygons]
        min_x, min_y, max_x, max_y = (
            min(b[0] for b in bounds),
            min(b[1] for b in bounds),
            max(b[2] for b in bounds),
            max(b[3] for b in bounds),
        )
        offset = Point(
            -min_x,
            -min_y,
        )

        if scale_to_fit and bbox:
            scale = min(bbox[0] / (max_x - min_x), bbox[1] / (max_y - min_y))

        logger.debug(f"Text size: {text_size}")
        logger.debug(f"Offset: {offset}")
        logger.debug(f"Scale: {scale}")

        polygons = flatten_polygons(polygons)
        polygons = [
            transform_polygon(p, scale=scale, offset=(offset.x, offset.y))
            for p in polygons
        ]

        # Invert the y-axis
        max_y = max(p.bounds[3] for p in polygons)
        polygons = [
            Polygon([(p[0], -p[1] + max_y) for p in polygon.exterior.coords])
            for polygon in polygons
        ]

        return polygons
