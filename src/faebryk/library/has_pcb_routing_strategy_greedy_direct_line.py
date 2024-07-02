# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging

from faebryk.exporters.pcb.kicad.transformer import PCB_Transformer
from faebryk.exporters.pcb.routing.util import (
    DEFAULT_TRACE_WIDTH,
    Route,
    apply_route_in_pcb,
    get_internal_nets_of_node,
    get_pads_pos_of_mifs,
)
from faebryk.library.has_overriden_name import has_overriden_name
from faebryk.library.has_pcb_routing_strategy import has_pcb_routing_strategy
from faebryk.library.Net import Net
from faebryk.libs.geometry.basic import Geometry

logger = logging.getLogger(__name__)


class has_pcb_routing_strategy_greedy_direct_line(has_pcb_routing_strategy.impl()):
    def calculate(self, transformer: PCB_Transformer):
        node = self.get_obj()
        nets = get_internal_nets_of_node(node)

        logger.debug(f"Routing {node} {'-'*40}")

        def get_route_for_net(net: Net, mifs) -> Route | None:
            if not net:
                return None
            net_name = net.get_trait(has_overriden_name).get_name()

            pads = get_pads_pos_of_mifs(mifs)

            if len(pads) < 2:
                return None

            logger.debug(f"Routing net {net_name} with pads: {pads}")

            sets = [{pad} for pad in pads.values()]

            route = Route(path=[])

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

                route.add(Route.Track(width=DEFAULT_TRACE_WIDTH, points=closest[3]))

            return route

        self.routes: dict[Net, Route] = {
            net: route
            for net, mifs in nets.items()
            if net
            and not net.has_trait(has_pcb_routing_strategy)
            and (route := get_route_for_net(net, mifs))
        }

        self.route = route

    def apply(self, transformer: PCB_Transformer):
        for net, route in self.routes.items():
            apply_route_in_pcb(net, route, transformer)
