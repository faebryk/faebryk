# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import itertools
import logging
import pprint
import random
import re
from abc import abstractmethod
from operator import add
from typing import Any, List, Tuple, TypeVar

import numpy as np
from faebryk.core.core import (
    Footprint as Core_Footprint,
)
from faebryk.core.core import (
    Module,
    ModuleInterface,
    ModuleInterfaceTrait,
    ModuleTrait,
    Node,
)
from faebryk.core.graph import Graph
from faebryk.library.has_footprint import has_footprint
from faebryk.library.has_kicad_footprint import has_kicad_footprint
from faebryk.library.has_overriden_name import has_overriden_name
from faebryk.library.has_pcb_position import has_pcb_position
from faebryk.library.Net import Net as FNet
from faebryk.libs.geometry.basic import Geometry
from faebryk.libs.kicad.pcb import (
    PCB,
    UUID,
    Arc,
    At,
    Font,
    Footprint,
    FP_Text,
    Geom,
    GR_Arc,
    GR_Line,
    GR_Text,
    Line,
    Net,
    Pad,
    Rect,
    Segment,
    Segment_Arc,
    Via,
)
from faebryk.libs.kicad.pcb import (
    Node as PCB_Node,
)

logger = logging.getLogger(__name__)


class PCB_Transformer:
    class has_linked_kicad_footprint(ModuleTrait):
        """
        Module has footprint (which has kicad footprint) and that footprint
        is found in the current PCB file.
        """

        @abstractmethod
        def get_fp(self) -> Footprint: ...

    class has_linked_kicad_footprint_defined(has_linked_kicad_footprint.impl()):
        def __init__(self, fp: Footprint) -> None:
            super().__init__()
            self.fp = fp

        def get_fp(self):
            return self.fp

    class has_linked_kicad_pad(ModuleInterfaceTrait):
        @abstractmethod
        def get_pad(self) -> tuple[Footprint, Pad]: ...

    class has_linked_kicad_pad_defined(has_linked_kicad_pad.impl()):
        def __init__(self, fp: Footprint, pad: Pad) -> None:
            super().__init__()
            self.fp = fp
            self.pad = pad

        def get_pad(self):
            return self.fp, self.pad

    def __init__(
        self, pcb: PCB, graph: Graph, app: Module, cleanup: bool = True
    ) -> None:
        self.pcb = pcb
        self.graph = graph
        self.app = app

        self.dimensions = None

        FONT_SCALE = 8
        FONT = Font.factory(
            size=(1 / FONT_SCALE, 1 / FONT_SCALE),
            thickness=0.15 / FONT_SCALE,
        )
        self.font = FONT

        # After finalized, vias get changed to 0.45
        self.via_size_drill = (0.46, 0.2)

        self.tstamp_i = itertools.count()
        self.cleanup()

        self.attach()

    def attach(self):
        footprints = {(f.reference.text, f.name): f for f in self.pcb.footprints}

        for node in {gif.node for gif in self.graph.G.nodes}:
            assert isinstance(node, Node)
            if not node.has_trait(has_overriden_name):
                continue
            if not node.has_trait(has_footprint):
                continue
            g_fp = node.get_trait(has_footprint).get_footprint()
            if not g_fp.has_trait(has_kicad_footprint):
                continue

            fp_ref = node.get_trait(has_overriden_name).get_name()
            fp_name = g_fp.get_trait(has_kicad_footprint).get_kicad_footprint()

            assert (
                fp_ref,
                fp_name,
            ) in footprints, (
                f"Footprint ({fp_ref=}, {fp_name=}) not found in footprints dictionary."
                f" Did you import the latest NETLIST into KiCad?"
            )
            fp = footprints[(fp_ref, fp_name)]

            node.add_trait(self.has_linked_kicad_footprint_defined(fp))

        # TODO implement above
        # way faster because can skip fp lookup
        for node in {gif.node for gif in self.graph.G.nodes}:
            assert isinstance(node, Node)
            if not isinstance(node, ModuleInterface):
                continue

            try:
                fp, pad = PCB_Transformer.get_pad(node)
            # TODO
            except Exception:
                continue

            node.add_trait(PCB_Transformer.has_linked_kicad_pad_defined(fp, pad))

        attached = {
            gif.node: gif.node.get_trait(self.has_linked_kicad_footprint).get_fp()
            for gif in self.graph.G.nodes
            if gif.node.has_trait(self.has_linked_kicad_footprint)
        }
        logger.debug(f"Attached: {pprint.pformat(attached)}")

    def cleanup(self):
        # delete auto-placed vias
        # determined by their size_drill values
        for via in self.pcb.vias:
            if via.size_drill == self.via_size_drill:
                via.delete()

        for text in self.pcb.text:
            if text.text.endswith("_FBRK_AUTO"):
                text.delete()

        # TODO maybe faebryk layer?
        CLEAN_LAYERS = re.compile(r"^User.[2-9]$")
        for geo in self.pcb.geoms:
            if CLEAN_LAYERS.match(geo.layer_name) is None:
                continue
            geo.delete()
        self.pcb.garbage_collect()

    T = TypeVar("T")

    @staticmethod
    def flipped(input_list: list[tuple[T, int]]) -> list[tuple[T, int]]:
        return [(x, (y + 180) % 360) for x, y in reversed(input_list)]

    def gen_tstamp(self):
        return str(next(self.tstamp_i))

    # Getter ---------------------------------------------------------------------------
    @staticmethod
    def get_fp(cmp) -> Footprint:
        return cmp.get_trait(PCB_Transformer.has_linked_kicad_footprint).get_fp()

    def get_net(self, net: FNet) -> Net:
        nets = {pcb_net.name: pcb_net for pcb_net in self.pcb.nets}
        return nets[net.get_trait(has_overriden_name).get_name()]

    def get_edge(self) -> list[GR_Line.Coord]:
        def geo_to_lines(
            geo: Geom, parent: PCB_Node
        ) -> list[tuple[GR_Line.Coord, GR_Line.Coord]]:
            lines = []
            assert geo.sym is not None

            if isinstance(geo, GR_Line):
                lines = [(geo.start, geo.end)]
            elif isinstance(geo, Arc):
                arc = (geo.start, geo.mid, geo.end)
                lines = Geometry.approximate_arc(*arc, resolution=10)
            elif isinstance(geo, Rect):
                rect = (geo.start, geo.end)

                c0 = (rect[0][0], rect[1][1])
                c1 = (rect[1][0], rect[0][1])

                l0 = (rect[0], c0)
                l1 = (rect[0], c1)
                l2 = (rect[1], c0)
                l3 = (rect[1], c1)

                lines = [l0, l1, l2, l3]
            else:
                raise NotImplementedError(f"Unsupported type {type(geo)}: {geo}")

            if geo.sym.startswith("fp"):
                assert isinstance(parent, Footprint)
                lines = [
                    tuple(Geometry.abs_pos(parent.at.coord, x) for x in line)
                    for line in lines
                ]

            return lines

        def quantize_line(line: tuple[GR_Line.Coord, GR_Line.Coord]):
            DIGITS = 2
            return tuple(tuple(round(c, DIGITS) for c in p) for p in line)

        lines: list[tuple[GR_Line.Coord, GR_Line.Coord]] = [
            quantize_line(line)
            for sub_lines in [
                geo_to_lines(pcb_geo, self.pcb)
                for pcb_geo in self.pcb.geoms
                if pcb_geo.layer_name == "Edge.Cuts"
            ]
            + [
                geo_to_lines(fp_geo, fp)
                for fp in self.pcb.footprints
                for fp_geo in fp.geoms
                if fp_geo.layer_name == "Edge.Cuts"
            ]
            for line in sub_lines
        ]

        if not lines:
            return []

        from shapely import (
            LineString,
            get_geometry,
            get_num_geometries,
            polygonize_full,
        )

        polys, cut_edges, dangles, invalid_rings = polygonize_full(
            [LineString(line) for line in lines]
        )

        if get_num_geometries(cut_edges) != 0:
            raise Exception(f"EdgeCut: Cut edges: {cut_edges}")

        if get_num_geometries(dangles) != 0:
            raise Exception(f"EdgeCut: Dangling lines: {dangles}")

        if get_num_geometries(invalid_rings) != 0:
            raise Exception(f"EdgeCut: Invald rings: {invalid_rings}")

        if (n := get_num_geometries(polys)) != 1:
            if n == 0:
                logger.warning(f"EdgeCut: No closed polygons found in {lines}")
                assert False  # TODO remove
                return []
            raise Exception(f"EdgeCut: Ambiguous polygons {polys}")

        return get_geometry(polys, 0).exterior.coords

    @staticmethod
    def get_corresponding_fp(
        intf: ModuleInterface,
    ) -> tuple[Core_Footprint, Module]:
        obj = intf

        while not obj.has_trait(has_footprint):
            parent = obj.get_parent()
            if parent is None:
                raise Exception
            obj = parent[0]

        assert isinstance(obj, Module)
        return obj.get_trait(has_footprint).get_footprint(), obj

    @staticmethod
    def get_pad(intf: ModuleInterface) -> tuple[Footprint, Pad]:
        cfp, obj = PCB_Transformer.get_corresponding_fp(intf)
        pin_map = cfp.get_trait(has_kicad_footprint).get_pin_names()
        cfg_if = [
            (pin, name) for pin, name in pin_map.items() if intf.is_connected_to(pin)
        ]
        assert len(cfg_if) == 1

        pin_name = cfg_if[0][1]

        fp = PCB_Transformer.get_fp(obj)
        pad = fp.get_pad(pin_name)

        return fp, pad

    def get_copper_layers(self):
        COPPER = re.compile(r"^.*\.Cu$")

        return {name for name in self.pcb.layer_names if COPPER.match(name) is not None}

    def get_copper_layers_pad(self, pad: Pad):
        COPPER = re.compile(r"^.*\.Cu$")

        all_layers = self.pcb.layer_names

        def dewildcard(layer: str):
            if "*" not in layer:
                return {layer}
            pattern = re.compile(layer.replace(".", r"\.").replace("*", r".*"))
            return {
                global_layer
                for global_layer in all_layers
                if pattern.match(global_layer) is not None
            }

        layers = pad.layers
        dewildcarded_layers = {
            sub_layer for layer in layers for sub_layer in dewildcard(layer)
        }
        matching_layers = {
            layer for layer in dewildcarded_layers if COPPER.match(layer) is not None
        }

        return matching_layers

    # Insert ---------------------------------------------------------------------------
    def insert(self, node: PCB_Node):
        self.pcb.append(node)

    # TODO
    def insert_plane(self, layer: str, net: Any):
        raise NotImplementedError()

    def insert_via(self, coord: tuple[float, float], net: str):
        self.insert(
            Via.factory(
                at=At.factory(coord),
                size_drill=self.via_size_drill,
                layers=("F.Cu", "B.Cu"),
                net=net,
                tstamp=self.gen_tstamp(),
            )
        )

    def insert_text(self, text: str, at: "At", font: Font, permanent: bool):
        # TODO find a better way for this
        if not permanent:
            text = text + "_FBRK_AUTO"
        self.insert(
            GR_Text.factory(
                text=text,
                at=at,
                layer="F.SilkS",
                font=font,
                tstamp=self.gen_tstamp(),
            )
        )

    def insert_track(
        self,
        net_id: int,
        points: list[Segment.Coord],
        width: float,
        layer: str,
        arc: bool,
    ):
        # TODO marker

        parts = []
        if arc:
            start_and_ends = points[::2]
            for s, e, m in zip(start_and_ends[:-1], start_and_ends[1:], points[1::2]):
                parts.append(
                    Segment_Arc.factory(
                        s,
                        m,
                        e,
                        width=width,
                        layer=layer,
                        net_id=net_id,
                        tstamp=self.gen_tstamp(),
                    )
                )
        else:
            for s, e in zip(points[:-1], points[1:]):
                parts.append(
                    Segment.factory(
                        s,
                        e,
                        width=width,
                        layer=layer,
                        net_id=net_id,
                        tstamp=self.gen_tstamp(),
                    )
                )

        for part in parts:
            self.insert(part)

    def insert_geo(self, geo: Geom):
        self.insert(geo)

    def insert_via_next_to(self, intf: ModuleInterface, clearance: tuple[float, float]):
        fp, pad = self.get_pad(intf)

        rel_target = tuple(map(add, pad.at.coord, clearance))
        coord = Geometry.abs_pos(fp.at.coord, rel_target)

        self.insert_via(coord[:2], pad.net)

        # print("Inserting via for", ".".join([y for x,y in intf.get_hierarchy()]),
        # "at:", coord, "in net:", net)
        ...

    def insert_via_triangle(
        self, intfs: list[ModuleInterface], depth: float, clearance: float
    ):
        # get pcb pads
        fp_pads = list(map(self.get_pad, intfs))
        pads = [x[1] for x in fp_pads]
        fp = fp_pads[0][0]

        # from first & last pad
        rect = [pads[-1].at.coord[i] - pads[0].at.coord[i] for i in range(2)]
        assert 0 in rect
        width = [p for p in rect if p != 0][0]
        start = pads[0].at.coord

        # construct triangle
        shape = Geometry.triangle(
            Geometry.abs_pos(fp.at.coord, start),
            width=width,
            depth=depth,
            count=len(pads),
        )

        # clearance
        shape = Geometry.translate(
            tuple([clearance if x != 0 else 0 for x in rect]), shape
        )

        # place vias
        for pad, point in zip(pads, shape):
            self.insert_via(point, pad.net)

    def insert_via_line(
        self,
        intfs: list[ModuleInterface],
        length: float,
        clearance: float,
        angle_deg: float,
    ):
        raise NotImplementedError()
        # get pcb pads
        fp_pads = list(map(self.get_pad, intfs))
        pads = [x[1] for x in fp_pads]
        fp = fp_pads[0][0]

        # from first & last pad
        start = pads[0].at.coord
        abs_start = Geometry.abs_pos(fp.at.coord, start)

        shape = Geometry.line(
            start=abs_start,
            length=length,
            count=len(pads),
        )

        shape = Geometry.rotate(
            axis=abs_start[:2],
            structure=shape,
            angle_deg=angle_deg,
        )

        # clearance
        shape = Geometry.translate((clearance, 0), shape)

        # place vias
        for pad, point in zip(pads, shape):
            self.insert_via(point, pad.net)

    def insert_via_line2(
        self,
        intfs: list[ModuleInterface],
        length: tuple[float, float],
        clearance: tuple[float, float],
    ):
        # get pcb pads
        fp_pads = list(map(self.get_pad, intfs))
        pads = [x[1] for x in fp_pads]
        fp = fp_pads[0][0]

        # from first & last pad
        start = tuple(map(add, pads[0].at.coord, clearance))
        abs_start = Geometry.abs_pos(fp.at.coord, start)

        shape = Geometry.line2(
            start=abs_start,
            end=Geometry.abs_pos(abs_start, length),
            count=len(pads),
        )

        # place vias
        for pad, point in zip(pads, shape):
            self.insert_via(point, pad.net)

    # Positioning ----------------------------------------------------------------------
    def move_footprints(self):
        # position modules with defined positions
        pos_mods: set[Module] = {
            gif.node
            for gif in self.graph.G.nodes
            if gif.node.has_trait(has_pcb_position)
            and gif.node.has_trait(self.has_linked_kicad_footprint)
        }
        logger.info(f"Positioning {len(pos_mods)} footprints")

        for module in pos_mods:
            fp = module.get_trait(self.has_linked_kicad_footprint).get_fp()
            coord = module.get_trait(has_pcb_position).get_position()
            layer_name = {
                has_pcb_position.layer_type.TOP_LAYER: "F.Cu",
                has_pcb_position.layer_type.BOTTOM_LAYER: "B.Cu",
            }

            if coord[3] == has_pcb_position.layer_type.NONE:
                raise Exception(f"Component {module}({fp.name}) has no layer defined")

            logger.debug(f"Placing {fp.name} at {coord} layer {layer_name[coord[3]]}")
            self.move_fp(fp, coord[:3], layer_name[coord[3]])

    def move_fp(self, fp: Footprint, coord: Footprint.Coord, layer: str):
        if any([x.text == "FBRK:notouch" for x in fp.user_text]):
            logger.warning(f"Skipped no touch component: {fp.name}")
            return

        # Rotate
        rot_angle = (coord[2] - fp.at.coord[2]) % 360

        if rot_angle:
            for at_prop in fp.get_prop("at", recursive=True):
                coords = at_prop.node[1:]
                # if rot is 0 in coord, its compressed to a 2-tuple by kicad
                if len(coords) == 2:
                    coords.append(0)
                coords[2] = (coords[2] + rot_angle) % 360
                at_prop.node[1:] = coords

        fp.at.coord = coord

        # Flip
        # TODO a bit ugly with the hardcoded front layer
        flip = layer != "F.Cu" and fp.layer != layer

        if flip:
            for layer_prop in fp.get_prop(["layer", "layers"], recursive=True):

                def _flip(x):
                    return (
                        x.replace("F.", "<F>.")
                        .replace("B.", "F.")
                        .replace("<F>.", "B.")
                    )

                layer_prop.node[1:] = [_flip(x) for x in layer_prop.node[1:]]

        # Label
        if any([x.text == "FBRK:autoplaced" for x in fp.user_text]):
            return
        fp.append(
            FP_Text.factory(
                text="FBRK:autoplaced",
                at=At.factory((0, 0, 0)),
                font=self.font,
                uuid=UUID.factory(),
                layer="User.5",
            )
        )

    # Edge -----------------------------------------------------------------------------
    # TODO: make generic
    def connect_lines_via_radius(
        self,
        line1: Line,
        line2: Line,
        radius: float,
    ) -> Tuple[GR_Line, GR_Arc, GR_Line]:
        def calculate_arc_coordinates(
            A: Tuple, B: Tuple, C: Tuple, r: float
        ) -> tuple[Geom.Coord, Geom.Coord, Geom.Coord]:
            # TODO: remove
            logger.setLevel(logging.DEBUG)
            # Calculate the vectors
            vector_ab = np.array([A[0] - B[0], A[1] - B[1]])
            vector_bc = np.array([C[0] - B[0], C[1] - B[1]])
            logger.debug(f"{'-'*21} Arc Calculations {'-'*21}")
            logger.debug(f"             Points: l1s{A}, l2s{B}, l2e{C}")
            logger.debug(f"             Radius: {r}")
            logger.debug(f"           Vector A: {vector_ab}")
            logger.debug(f"           Vector B: {vector_bc}")

            # Normalize the vectors
            length_vector_ab = np.linalg.norm(vector_ab)
            length_vector_bc = np.linalg.norm(vector_bc)
            unitvector_ab = vector_ab / length_vector_ab
            unitvector_bc = vector_bc / length_vector_bc
            logger.debug(f"   Length Vector AB: {length_vector_ab}")
            logger.debug(f"   Length Vector BC: {length_vector_bc}")
            logger.debug(f"  Normalized Vec AB: {unitvector_ab}")
            logger.debug(f"  Normalized Vec BC: {unitvector_bc}")

            # Calculate the angle between the unit vectors by using the dot product
            dot_product = np.dot(unitvector_ab, unitvector_bc)
            logger.debug(f"        Dot Product: {dot_product}")
            # clamp the dot product between -1 and 1
            angle = np.arccos(np.clip(dot_product, -1.0, 1.0))
            angle_half = angle / 2
            logger.debug(f"            Angle/2: {angle_half}")
            logger.debug(f"        Angle/2 deg: {np.degrees(angle_half)}")

            # find the unit bisector vector
            bisector = (unitvector_ab + unitvector_bc) / np.linalg.norm(
                unitvector_ab + unitvector_bc
            )
            logger.debug(f"       Bisector Vec: {bisector}")

            # Calculate distance from B to arc_center
            dist_to_center = r / np.sin(angle_half)
            logger.debug(f" Dist to Arc Center: {dist_to_center}")
            # check if dist_to_center in not more than AB or BC
            # if it is, reduce the radius
            if dist_to_center > min(length_vector_ab, length_vector_bc):
                logger.warning("Reducing radius")
                r = dist_to_center * np.abs(np.tan(angle_half / 2))

            # Calculate arc_center
            arc_center = np.array(B) - bisector * (dist_to_center / -1)

            # Calculate arc start and end points
            arc_start = np.array(B) + unitvector_ab * (r / np.tan(angle_half))
            arc_end = np.array(B) + unitvector_bc * (r / np.tan(angle_half))

            logger.debug(f"          Arc Start: {arc_start}")
            logger.debug(f"            Arc End: {arc_end}")
            logger.debug(f"         Arc Center: {arc_center}")

            logger.debug("")
            # TODO: remove
            logger.setLevel(logging.INFO)

            return (arc_start, arc_center, arc_end)

        # Extract coordinates from lines
        line1_start = line1.start
        line1_end = line1.end
        line2_start = line2.start
        line2_end = line2.end

        # Assert if the endpoints of the lines are not connected
        assert line1_end == line2_start, "The endpoints of the lines are not connected."

        # Assert if the radius is less than or equal to zero
        assert radius > 0, "The radius must be greater than zero."

        # Calculate the arc points
        arc_start, arc_center, arc_end = calculate_arc_coordinates(
            line1_start, line2_start, line2_end, radius
        )

        # Create the arc
        arc = GR_Arc.factory(
            start=arc_start,
            mid=arc_center,
            end=arc_end,
            stroke=GR_Line.Stroke.factory(0.05, "default"),
            layer="Edge.Cuts",
            tstamp=str(int(random.random() * 100000)),
        )

        # Create new lines
        new_line1 = GR_Line.factory(
            start=line1_start,
            end=arc_start,
            stroke=GR_Line.Stroke.factory(0.05, "default"),
            layer="Edge.Cuts",
            tstamp=str(int(random.random() * 100000)),
        )
        new_line2 = GR_Line.factory(
            start=arc_end,
            end=line2_end,
            stroke=GR_Line.Stroke.factory(0.05, "default"),
            layer="Edge.Cuts",
            tstamp=str(int(random.random() * 100000)),
        )

        return new_line1, arc, new_line2

    def create_rectangular_edgecut(
        self,
        width_mm: float,
        height_mm: float,
        rounded_corners: bool = False,
        corner_radius_mm: float = 0.0,
    ) -> List[Geom] | List[GR_Line]:
        """
        Create a rectengular board outline (edge cut)
        """
        # make 4 line objects where the end of the last line is the begining of the next
        lines = [
            GR_Line.factory(
                start=(0, 0),
                end=(width_mm, 0),
                stroke=GR_Line.Stroke.factory(0.05, "default"),
                layer="Edge.Cuts",
                tstamp=str(int(random.random() * 100000)),
            ),
            GR_Line.factory(
                start=(width_mm, 0),
                end=(width_mm, height_mm),
                stroke=GR_Line.Stroke.factory(0.05, "default"),
                layer="Edge.Cuts",
                tstamp=str(int(random.random() * 100000)),
            ),
            GR_Line.factory(
                start=(width_mm, height_mm),
                end=(0, height_mm),
                stroke=GR_Line.Stroke.factory(0.05, "default"),
                layer="Edge.Cuts",
                tstamp=str(int(random.random() * 100000)),
            ),
            GR_Line.factory(
                start=(0, height_mm),
                end=(0, 0),
                stroke=GR_Line.Stroke.factory(0.05, "default"),
                layer="Edge.Cuts",
                tstamp=str(int(random.random() * 100000)),
            ),
        ]
        if rounded_corners:
            rectangle_geometry = []
            # calculate from a line pair sharing a corner, a line pair with an arc in
            # between using connect_lines_via_radius.
            # replace the original line pair with the new line pair and arc
            for i in range(len(lines)):
                line1 = lines[i]
                line2 = lines[(i + 1) % len(lines)]
                new_line1, arc, new_line2 = self.connect_lines_via_radius(
                    line1,
                    line2,
                    corner_radius_mm,
                )
                lines[i] = new_line1
                lines[(i + 1) % len(lines)] = new_line2
                rectangle_geometry.append(arc)
            for line in lines:
                rectangle_geometry.append(line)

            return rectangle_geometry
        else:
            # Create the rectangle without rounded corners using lines
            return lines

    # plot the board outline with matplotlib
    # TODO: remove
    def plot_board_outline(self, geometry: List[Any]):
        import matplotlib.patches as patches
        import matplotlib.pyplot as plt
        from matplotlib.path import Path

        def plot_arc(start, mid, end):
            verts = [start, mid, end]
            codes = [Path.MOVETO, Path.CURVE3, Path.CURVE3]  # , Path.CLOSEPOLY]

            path = Path(verts, codes)
            shape = patches.PathPatch(path, facecolor="none", lw=0.75)
            plt.gca().add_patch(shape)

        fig, ax = plt.subplots()
        for geo in geometry:
            if isinstance(geo, GR_Line):
                # plot a line
                plt.plot([geo.start[0], geo.end[0]], [geo.start[1], geo.end[1]])
            elif isinstance(geo, GR_Arc):
                plot_arc(geo.start, geo.mid, geo.end)
                plt.plot([geo.start[0], geo.end[0]], [geo.start[1], geo.end[1]])
        plt.show()

    def set_pcb_outline_complex(
        self,
        geometry: List[Geom] | List[GR_Line],
        remove_existing_outline: bool = True,
    ):
        """
        Create a board outline (edge cut) consisting out of
        different geometries
        """

        # TODO: remove
        # self.plot_board_outline(geometry)

        # remove existing lines on Egde.cuts layer
        if remove_existing_outline:
            for geo in self.pcb.geoms:
                if geo.sym not in ["gr_line", "gr_arc"]:
                    continue
                if geo.layer_name != "Edge.Cuts":
                    continue
                geo.delete()

        # create Edge.Cuts geometries
        for geo in geometry:
            assert (
                geo.layer_name == "Edge.Cuts"
            ), f"Geometry {geo} is not on Edge.Cuts layer"

            self.pcb.append(geo)

        # find bounding box
