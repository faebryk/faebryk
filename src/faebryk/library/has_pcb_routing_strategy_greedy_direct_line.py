# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging
from typing import Sequence

from faebryk.core.core import Node
from faebryk.core.util import get_all_nodes, get_net
from faebryk.exporters.pcb.kicad.transformer import PCB_Transformer
from faebryk.library.Electrical import Electrical
from faebryk.library.has_overriden_name import has_overriden_name
from faebryk.library.has_pcb_routing_strategy import has_pcb_routing_strategy
from faebryk.library.Net import Net
from faebryk.libs.geometry.basic import Geometry
from faebryk.libs.util import groupby

logger = logging.getLogger(__name__)


def get_nets_of_node(node: Node):
    mifs = {n for n in get_all_nodes(node) if isinstance(n, Electrical)}
    nets = groupby(mifs, lambda mif: get_net(mif))

    return nets


def get_pad_pos_of_mif(mif: Electrical):
    if not mif.has_trait(PCB_Transformer.has_linked_kicad_pad):
        return None

    fp, pad = mif.get_trait(PCB_Transformer.has_linked_kicad_pad).get_pad()
    return Geometry.abs_pos(fp.at.coord, pad.at.coord)


def get_pads_pos_of_mifs(mifs: Sequence[Electrical]):
    # TODO layer
    pads = {mif: pos for mif in mifs if (pos := get_pad_pos_of_mif(mif)) is not None}

    return pads


class has_pcb_routing_strategy_greedy_direct_line(has_pcb_routing_strategy.impl()):
    def calculate(self):
        node = self.get_obj()
        nets = get_nets_of_node(node)

        logger.debug(f"Routing {node} {'-'*40}")

        def get_route_for_net(net: Net, mifs):
            if not net:
                return None
            net_name = net.get_trait(has_overriden_name).get_name()

            pads = get_pads_pos_of_mifs(mifs)

            if len(pads) < 2:
                return None

            logger.debug(f"Routing net {net_name} with pads: {pads}")

            sets = [{pad} for pad in pads.values()]
            tracks: list[list[Geometry.Point]] = []

            # TODO avoid crossing pads
            # might make this very complex though

            while len(sets) > 1:
                # find closest pads
                closest = min(
                    (
                        (set1, set2, Geometry.distance_euclid(p1, p2), [p1, p2])
                        for set1 in sets
                        for set2 in sets
                        for p1 in set1
                        for p2 in set2
                        if set1 != set2
                    ),
                    key=lambda t: t[2],
                )

                # merge closest pads
                sets.remove(closest[0])
                sets.remove(closest[1])
                sets.append(closest[0].union(closest[1]))
                tracks.append(closest[3])

            return tracks

        route: dict[Net, list[list[Geometry.Point]]] = {
            net: tracks
            for net, mifs in nets.items()
            if net and (tracks := get_route_for_net(net, mifs))
        }

        self.route = route

    def apply(self, transformer: PCB_Transformer):
        for net, tracks in self.route.items():
            pcb_net = transformer.get_net(net)

            # build track
            logger.debug(
                f"Insert tracks for net {pcb_net.name}, {pcb_net.id}, {tracks}"
            )
            for track in tracks:
                path = [(round(p[0], 2), round(p[1], 2)) for p in track]

                transformer.insert_track(
                    net_id=pcb_net.id,
                    points=path,
                    width=0.1,
                    layer="F.Cu",
                    arc=False,
                )
