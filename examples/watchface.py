# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

"""
This file contains a faebryk sample.
Faebryk samples demonstrate the usage by building example systems.
"""
import logging
from datetime import datetime, timedelta
from pathlib import Path

import typer
from faebryk.core.core import (
    GraphInterfaceSelf,
    Module,
    Parameter,
    Trait,
)
from faebryk.core.graph import Graph
from faebryk.core.util import connect_all_interfaces, get_all_nodes, get_connected_mifs
from faebryk.library.Constant import Constant
from faebryk.library.Geometry import (
    Anchor,
    Circle,
    Line,
    PixelSpace,
    Space,
    Translation,
    Vector,
    can_be_projected_into_vector_space,
    can_be_projected_into_vector_space_defined,
    does_operations_in_vector_space,
)
from faebryk.library.TBD import TBD
from faebryk.libs.experiments.buildutil import export_graph
from faebryk.libs.logging import setup_basic_logging
from faebryk.libs.util import times, zip_rotate
from PIL import Image, ImageDraw

logger = logging.getLogger(__name__)

# logger.setLevel(logging.DEBUG)


class show(Trait):
    ...


def make_points_from_graph(G: Graph, space: Space) -> list[Vector]:
    points: list[Vector] = []
    used = set()
    explore = set(gif.node for gif in G.G.nodes if isinstance(gif, GraphInterfaceSelf))

    while len(explore - used) > 0:
        node = next(iter((explore - used)))
        explore.remove(node)

        if node.has_trait(can_be_projected_into_vector_space):
            used.add(node)
            logger.debug(f"Found {node}")
            vecs = node.get_trait(can_be_projected_into_vector_space).project(space)
            logger.debug(f"\tExtending by {vecs}")
            if node.has_trait(show):
                points.extend(vecs)

            if isinstance(node, Anchor):
                assert len(vecs) == 1
                vec = vecs[0]
                mifs = get_connected_mifs(node.GIFs.connected)
                for mif in mifs:
                    logger.debug(f"\tNeighbor anchor {mif}")
                    assert isinstance(mif, Anchor)
                    mif.add_trait(can_be_projected_into_vector_space_defined(vec))
                    explore |= set(n for n, _ in mif.get_hierarchy())

        if node.has_trait(does_operations_in_vector_space):
            used.add(node)
            logger.debug(f"Found op {node}")
            modified = node.get_trait(does_operations_in_vector_space).execute(space)
            explore |= set(n for mod in modified for n, _ in mod.get_hierarchy())

    return points


class WatchFace(Module):
    def __init__(self, outer_radius: Parameter, general_quant: Parameter) -> None:
        super().__init__()

        class IFS(Module.IFS()):
            center = Anchor()

        self.IFs = IFS(self)

        class NODES(Module.NODES()):
            base = Circle(outer_radius)
            markers = times(12, Line)
            hands = times(3, Line)

        self.NODEs = NODES(self)

        self.quant = general_quant

        inner_circle = Circle(TBD())
        inner_circle.IFs.center.connect(self.NODEs.base.IFs.center)
        Translation(self.quant).translate(
            self.NODEs.base.IFs.radius, inner_circle.IFs.radius
        )
        marks = times(12, Anchor)

        # set center to watch center
        self.IFs.center.connect(self.NODEs.base.IFs.center)

        # connect hands to middle
        connect_all_interfaces(
            [self.NODEs.base.IFs.center] + [p.IFs.ends[0] for p in self.NODEs.hands],
        )

        for i, (mark, marker) in enumerate(zip(marks, self.NODEs.markers)):
            angle_deg = Constant(i * 360 / len(marks))

            # create marks at hour marks
            mark.connect(self.NODEs.base.on_arc(angle_deg))

            # connect markers to marks
            marker.IFs.ends[0].connect(mark)

            # extend markers
            marker.IFs.ends[1].connect(inner_circle.on_arc(angle_deg))

    def set_time(self, time: datetime):
        # TODO can only be done once like this

        def circle(i: int):
            out = Circle(TBD())
            out.IFs.center.connect(self.NODEs.base.IFs.center)
            Translation(self.quant).translate(
                self.NODEs.base.IFs.radius, out.IFs.radius, i
            )
            return out

        s = time.second / 60
        m = (time.minute + s) / 60
        h = (time.hour % 12 + m) / 12

        self.NODEs.hands[0].IFs.ends[1].connect(circle(2).on_arc(Constant(h * 360)))
        self.NODEs.hands[1].IFs.ends[1].connect(circle(1).on_arc(Constant(m * 360)))
        self.NODEs.hands[2].IFs.ends[1].connect(circle(0).on_arc(Constant(s * 360)))


class PolyLine(Module):
    def __init__(self, points: list[Anchor]) -> None:
        super().__init__()

        class IFS(Module.IFS()):
            ...

        self.IFs = IFS(self)

        class NODES(Module.NODES()):
            raw_lines = times(len(points), Line)

        self.NODEs = NODES(self)

        for line_prev, line_next in zip_rotate(self.NODEs.raw_lines):
            line_prev.IFs.ends[1].connect(line_next.IFs.ends[0])

        for point, line in zip(points, self.NODEs.raw_lines):
            line.IFs.ends[0].connect(point)


def _coordinate_anchor(vector: Vector, reference: Anchor) -> Anchor:
    return Translation(Constant(vector)).translate(reference, Anchor())


class FaebrykLogo(Module):
    def __init__(self, scale: float) -> None:
        super().__init__()

        class IFS(Module.IFS()):
            center = Anchor()

        self.IFs = IFS(self)

        coords = {
            "A": (0.0, 0.0),
            "B": (20.0, 0.0),
            "C": (30.0, 0.0),
            "D": (30.0, 10.0),
            "E": (10.0, 10.0),
            "F": (10.0, 20.0),
            "G": (5.0, 25.0),
            "H": (30.0, 20.0),
            "I": (30.0, 30.0),
            "J": (10.0, 30.0),
            "K": (10.0, 35.0),
            "L": (10.0, 45.0),
            "M": (0.0, 45.0),
            "N": (0.0, 30.0),
            "O": (0.0, 15.0),
        }

        dimensions = (
            PixelSpace.PixelVector(
                *[max([c[i] for c in coords.values()]) for i in range(2)]
            )
            * scale
        )

        origin = Translation(Constant(dimensions / 2 * -1)).translate(
            self.IFs.center, Anchor()
        )

        anchors = {
            k: _coordinate_anchor(PixelSpace.PixelVector(*v) * scale, origin)
            for k, v in coords.items()
        }

        f_coords = ["A", "C", "D", "E", "F", "H", "I", "J", "L", "M"]
        node_coords = ["A", "B", "C", "D", "E", "G", "H", "I", "K", "L", "M", "N", "O"]
        edge_coords = [
            ("A", "E"),
            ("B", "E"),
            ("B", "D"),
            ("C", "E"),
            ("E", "O"),
            ("H", "G"),
            ("I", "G"),
            ("N", "K"),
            ("N", "L"),
            ("M", "K"),
            ("J", "L"),
            ("K", "G"),
            ("N", "G"),
            ("O", "G"),
        ]

        node_radius = 0.55 * scale

        def _resolve(points: list[str]):
            return [anchors[point] for point in points]

        def _resolve_pairs(pairs: list[tuple[str, str]]):
            for pair in pairs:
                resolved = _resolve(list(pair))
                out = Line()
                out.IFs.ends[0].connect(resolved[0])
                out.IFs.ends[1].connect(resolved[1])
                yield out

        def _circle(point: Anchor):
            out = Circle(Constant(PixelSpace.PixelVector(node_radius, node_radius)))
            out.IFs.center.connect(point)
            return out

        class NODES(Module.NODES()):
            dots = [_circle(anchor) for anchor in _resolve(node_coords)]
            outline = list(_resolve_pairs(edge_coords))
            f = PolyLine(_resolve(f_coords))

        self.NODEs = NODES(self)


class App(Module):
    def __init__(self, size: PixelSpace.PixelVector) -> None:
        super().__init__()

        class IFS(Module.IFS()):
            ...

        self.IFs = IFS(self)

        min_dim = min(size.coords)

        class NODES(Module.NODES()):
            space = PixelSpace(size)
            watch = WatchFace(
                Constant(PixelSpace.PixelVector(0, -min_dim / 2)),
                Constant(PixelSpace.PixelVector(0, min_dim / 5 / 2)),
            )
            logo = FaebrykLogo(min_dim / 90)

        self.NODEs = NODES(self)

        center = self.NODEs.watch.IFs.center

        space_center = self.NODEs.space.dimensions / 2

        Translation(Constant(space_center)).translate(
            self.NODEs.space.NODEs.zero, center
        )

        Translation(Constant(space_center)).translate(
            self.NODEs.space.NODEs.zero, self.NODEs.logo.IFs.center
        )

        # render
        for n in self.NODEs.watch.NODEs.get_all():
            n.add_trait(show.impl()())
        for n in get_all_nodes(self.NODEs.logo):
            n.add_trait(show.impl()())


def main(make_graph: bool = True, show_graph: bool = True):
    app = App(PixelSpace.PixelVector(100, 100) * 8)
    app.NODEs.watch.set_time(datetime.now())
    # Export
    G = app.get_graph()

    logger.debug(f"Graph: {G.G}")

    # t1 = make_t1_netlist_from_graph(G)
    # t2 = make_t2_netlist_from_t1(t1)
    # netlist = from_faebryk_t2_netlist(t2)

    points = make_points_from_graph(G, app.NODEs.space)

    if make_graph:
        export_graph(G.G, show_graph)
    # export_netlist(netlist)

    build_folder = Path(__file__).parent.parent / "build"

    img = Image.new(
        "RGBA", (app.NODEs.space.dimensions.x, app.NODEs.space.dimensions.y)
    )
    img_context = ImageDraw.Draw(img)

    for point in points:
        img_context.point(point.coords)

    img.save(build_folder / "img.bmp")


def main_gif():
    img_size = PixelSpace.PixelVector(100, 100) * 8

    def clock_at_time(time: datetime):
        app = App(img_size)
        app.NODEs.watch.set_time(time)
        G = app.get_graph()
        points = make_points_from_graph(G, app.NODEs.space)

        img = Image.new(
            "RGB", (app.NODEs.space.dimensions.x, app.NODEs.space.dimensions.y)
        )
        img_context = ImageDraw.Draw(img)

        for point in points:
            img_context.point(point.coords)

        return img

    build_folder = Path(__file__).parent.parent / "build"

    now = datetime.now()
    img_frames = [clock_at_time(now + timedelta(seconds=i)) for i in range(60 * 5)]

    img_frames[0].save(
        build_folder / "clock.gif",
        save_all=True,
        append_images=img_frames[1:],
        optimize=True,
        duration=100,  # ms
        loop=0,  # 0 is infinite loop
    )


if __name__ == "__main__":
    setup_basic_logging()
    logger.info("Running experiment")

    typer.run(main_gif)
