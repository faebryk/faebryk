# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging
from dataclasses import dataclass
from typing import Sequence

from faebryk.core.core import Node
from faebryk.core.util import get_all_nodes, get_connected_mifs, get_net
from faebryk.exporters.pcb.kicad.transformer import PCB_Transformer
from faebryk.library.Electrical import Electrical
from faebryk.library.Net import Net
from faebryk.libs.geometry.basic import Geometry

# logging settings
logger = logging.getLogger(__name__)


# TODO remove
DEFAULT_TRACE_WIDTH = 0.1
DEFAULT_VIA_SIZE_DRILL = (0.45, 0.25)


@dataclass
class Route:
    @dataclass
    class Obj: ...

    @dataclass
    class Trace(Obj):
        width: float

    @dataclass
    class Line(Trace):
        start: Geometry.Point
        end: Geometry.Point

    @dataclass
    class Track(Trace):
        points: Sequence[Geometry.Point]

    @dataclass
    class Via(Obj):
        pos: Geometry.Point
        size_drill: tuple[float, float]

    path: list[Obj]

    def add(self, obj: Obj):
        self.path.append(obj)


def apply_route_in_pcb(net: Net, route: Route, transformer: PCB_Transformer):
    pcb_net = transformer.get_net(net)

    logger.debug(f"Insert tracks for net {pcb_net.name}, {pcb_net.id}, {route}")

    for obj in route.path:
        if isinstance(obj, Route.Track):
            # path = [round(p, 2).twod() for p in obj.points]
            path = [(round(p[0], 2), round(p[1], 2)) for p in obj.points]

            transformer.insert_track(
                net_id=pcb_net.id,
                points=path,
                width=obj.width,
                layer="F.Cu",
                arc=False,
            )
        elif isinstance(obj, Route.Line):
            transformer.insert_track(
                net_id=pcb_net.id,
                points=[
                    (round(obj.start[0], 2), round(obj.start[1], 2)),
                    (round(obj.end[0], 2), round(obj.end[1], 2)),
                ],
                width=obj.width,
                layer="F.Cu",
                arc=False,
            )
        elif isinstance(obj, Route.Via):
            # coord = round(obj.pos, 2).twod()
            coord = round(obj.pos[0], 2), round(obj.pos[1], 2)

            transformer.insert_via(
                net=pcb_net.id,
                coord=coord,
                size_drill=obj.size_drill,
            )


def get_internal_nets_of_node(node: Node):
    """
    Returns all Nets occuring (at least partially) within Node
    and returns for each of those the corresponding mifs
    For Nets returns all connected mifs
    """

    from faebryk.libs.util import groupby

    if isinstance(node, Net):
        return {node: get_connected_mifs(node.IFs.part_of.GIFs.connected)}

    mifs = {n for n in get_all_nodes(node) if isinstance(n, Electrical)}
    nets = groupby(mifs, lambda mif: get_net(mif))

    return nets


def get_pad_pos_of_mif(mif: Electrical):
    if not mif.has_trait(PCB_Transformer.has_linked_kicad_pad):
        return None

    return PCB_Transformer.get_pad_pos(mif)


def get_pads_pos_of_mifs(mifs: Sequence[Electrical]):
    return {mif: pos for mif in mifs if (pos := get_pad_pos_of_mif(mif)) is not None}
