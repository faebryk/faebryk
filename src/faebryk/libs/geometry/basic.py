# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging
import math
from math import inf
from operator import add
from typing import TypeVar

import numpy as np
from shapely import Point, Polygon, transform

logger = logging.getLogger(__name__)


def fill_poly_with_nodes_on_grid(
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


def transform_polygons(
    polys: list[list[Polygon]], dim: tuple[float, float, float, float]
) -> list[list[Polygon]]:
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
            transform(poly, lambda x: (x + [offset_x, offset_y]) * [scale_x, scale_y])
        )

    return scaled_polys


# TODO: cleanup and merge
class Geometry:
    Point2D = tuple[float, float]
    # TODO fix all Point2D functions to use Point

    # TODO more generic
    # x,y, rotation, layer
    Point = tuple[float, float, float, int]

    @staticmethod
    def mirror(axis: tuple[float | None, float | None], structure: list[Point2D]):
        return [
            (
                2 * axis[0] - x if axis[0] is not None else x,
                2 * axis[1] - y if axis[1] is not None else y,
            )
            for (x, y) in structure
        ]

    @staticmethod
    def abs_pos(parent: Point, child: Point) -> Point:
        rot_deg = parent[2] + child[2]

        rot = rot_deg / 360 * 2 * math.pi

        x, y = parent[:2]
        cx, cy = child[:2]

        rx = round(cx * math.cos(rot) + cy * math.sin(rot), 2)
        ry = round(-cx * math.sin(rot) + cy * math.cos(rot), 2)

        # print(f"Rotate {round(cx,2),round(cy,2)},
        # by {round(rot,2),parent[2]} to {rx,ry}")

        # TODO not sure what this is supposed to do
        # for i in range(2, len(parent)):
        #    if len(child) <= i:
        #        continue
        #    if parent[i] != 0 and child[i] != 0:
        #        logger.warn(f"Adding non-zero values: {parent[i]=} + {child[i]=}")

        # TODO check if this works everywhere
        out = (
            # XY
            x + rx,
            y + ry,
            # ROT
            *(c1 + c2 for c1, c2 in zip(parent[2:3], child[2:3])),
            # Layer
            child[3],
        )

        return out

    @staticmethod
    def translate(vec: Point2D, structure: list[Point2D]) -> list[Point2D]:
        return [tuple(map(add, vec, point)) for point in structure]

    @classmethod
    def rotate(
        cls, axis: Point2D, structure: list[Point2D], angle_deg: float
    ) -> list[Point2D]:
        theta = np.radians(angle_deg)
        c, s = np.cos(theta), np.sin(theta)
        R = np.array(((c, -s), (s, c)))

        return cls.translate(
            (-axis[0], -axis[1]),
            [tuple(R @ np.array(point)) for point in cls.translate(axis, structure)],
        )

    C = TypeVar("C", tuple[float, float], tuple[float, float, float])

    @staticmethod
    def triangle(start: C, width: float, depth: float, count: int):
        x1, y1 = start[:2]

        n = count - 1
        cy = width / n

        ys = [round(y1 + cy * i, 2) for i in range(count)]
        xs = [round(x1 + depth * (1 - abs(1 - 1 / n * i * 2)), 2) for i in range(count)]

        return list(zip(xs, ys))

    @staticmethod
    def line(start: C, length: float, count: int):
        x1, y1 = start[:2]

        n = count - 1
        cy = length / n

        ys = [round(y1 + cy * i, 2) for i in range(count)]
        xs = [x1] * count

        return list(zip(xs, ys))

    @staticmethod
    def line2(start: C, end: C, count: int):
        x1, y1 = start[:2]
        x2, y2 = end[:2]

        n = count - 1
        cx = (x2 - x1) / n
        cy = (y2 - y1) / n

        ys = [round(y1 + cy * i, 2) for i in range(count)]
        xs = [round(x1 + cx * i, 2) for i in range(count)]

        return list(zip(xs, ys))

    @staticmethod
    def find_circle_center(p1, p2, p3):
        """
        Finds the center of the circle passing through the three given points.
        """
        # Compute the midpoints
        mid1 = (p1 + p2) / 2
        mid2 = (p2 + p3) / 2

        # Compute the slopes of the lines
        m1 = (p2[1] - p1[1]) / (p2[0] - p1[0])
        m2 = (p3[1] - p2[1]) / (p3[0] - p2[0])

        # The slopes of the perpendicular bisectors
        perp_m1 = -1 / m1
        perp_m2 = -1 / m2

        # Equations of the perpendicular bisectors
        # y = perp_m1 * (x - mid1[0]) + mid1[1]
        # y = perp_m2 * (x - mid2[0]) + mid2[1]

        # Solving for x
        x = (mid2[1] - mid1[1] + perp_m1 * mid1[0] - perp_m2 * mid2[0]) / (
            perp_m1 - perp_m2
        )

        # Solving for y using one of the bisector equations
        y = perp_m1 * (x - mid1[0]) + mid1[1]

        return np.array([x, y])

    @staticmethod
    def approximate_arc(p_start, p_mid, p_end, resolution=10):
        p_start, p_mid, p_end = (np.array(p) for p in (p_start, p_mid, p_end))

        # Calculate the center of the circle
        center = Geometry.find_circle_center(p_start, p_mid, p_end)

        # Calculate start, mid, and end angles
        start_angle = np.arctan2(p_start[1] - center[1], p_start[0] - center[0])
        mid_angle = np.arctan2(p_mid[1] - center[1], p_mid[0] - center[0])
        end_angle = np.arctan2(p_end[1] - center[1], p_end[0] - center[0])

        # Adjust angles if necessary
        if start_angle > mid_angle:
            start_angle -= 2 * np.pi
        if mid_angle > end_angle:
            mid_angle -= 2 * np.pi

        # Radius of the circle
        r = np.linalg.norm(p_start - center)

        # Compute angles of line segment endpoints
        angles = np.linspace(start_angle, end_angle, resolution + 1)

        # Compute points on the arc
        points = np.array(
            [[center[0] + r * np.cos(a), center[1] + r * np.sin(a)] for a in angles]
        )

        # Create line segments
        segments = [(points[i], points[i + 1]) for i in range(resolution)]

        seg_no_np = [(tuple(a), tuple(b)) for a, b in segments]

        return seg_no_np
