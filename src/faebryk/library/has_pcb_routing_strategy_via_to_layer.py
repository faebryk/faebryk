# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging

from faebryk.exporters.pcb.kicad.transformer import PCB_Transformer
from faebryk.exporters.pcb.routing.util import (
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


class has_pcb_routing_strategy_via_to_layer(has_pcb_routing_strategy.impl()):
    def __init__(self, layer: str, vec: Geometry.Point2D):
        super().__init__()
        self.vec = vec
        self.layer = layer

    def calculate(self, transformer: PCB_Transformer):
        copper_layers = {
            layer: i for i, layer in enumerate(transformer.get_copper_layers())
        }
        layer = copper_layers[self.layer]

        node = self.get_obj()
        nets = get_internal_nets_of_node(node)

        logger.debug(f"Routing {node} {'-'*40}")

        def get_route_for_net(net: Net, mifs) -> Route | None:
            net_name = net.get_trait(has_overriden_name).get_name()

            pads = get_pads_pos_of_mifs(mifs)

            logger.debug(f"Routing net {net_name} with pads: {pads}")

            route = Route(path=[])

            for _, pos in pads.items():
                # No need to add via if on same layer already
                if pos[3] == layer:
                    continue
                via_pos: Geometry.Point = Geometry.add_points(pos, self.vec)
                route.add(Route.Via(via_pos))
                route.add(Route.Line(pos, via_pos))

            return route

        self.routes: dict[Net, Route] = {
            net: route
            for net, mifs in nets.items()
            if net and (route := get_route_for_net(net, mifs))
        }

    def apply(self, transformer: PCB_Transformer):
        for net, route in self.routes.items():
            apply_route_in_pcb(net, route, transformer)
