# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging
from dataclasses import dataclass

from faebryk.core.core import Module
from faebryk.core.util import get_all_nodes_graph
from faebryk.library.has_footprint import has_footprint
from faebryk.library.has_type_description import has_type_description

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class Component:
    name: str
    value: str
    properties: dict

    def __hash__(self) -> int:
        return hash((self.name, self.value, self.properties["footprint"]))


@dataclass(frozen=True)
class Vertex:
    component: Component
    pin: str


@dataclass(frozen=True)
class Net:
    properties: dict
    vertices: list[Vertex]


def make_t2_netlist_from_graph(G):
    from faebryk.core.graph import Graph
    from faebryk.exporters.netlist.graph import can_represent_kicad_footprint
    from faebryk.library.Net import Net as FNet

    assert isinstance(G, Graph)

    nets = {n for n in get_all_nodes_graph(G.G) if isinstance(n, FNet)}

    t2_nets = [
        Net(
            properties={
                "name": net.get_trait(has_type_description).get_type_description()
            },
            vertices=[
                Vertex(
                    component=t.get_kicad_obj(),
                    pin=t.get_pin_name(mif),
                )
                for mif, fp in net.get_fps().items()
                if (t := fp.get_trait(can_represent_kicad_footprint)) is not None
            ],
        )
        for net in nets
    ]

    comps = {
        n.get_trait(has_footprint)
        .get_footprint()
        .get_trait(can_represent_kicad_footprint)
        .get_kicad_obj()
        for gif in G.G.nodes
        if (n := gif.node).has_trait(has_footprint) and isinstance(n, Module)
    }

    assert all(vertex.component in comps for net in t2_nets for vertex in net.vertices)

    return {"nets": t2_nets, "comps": comps}
