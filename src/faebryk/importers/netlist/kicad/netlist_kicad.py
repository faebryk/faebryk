# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

from pathlib import Path

from faebryk.exporters.netlist.netlist import T2Netlist
from faebryk.libs.kicad.fileformats import C_kicad_netlist_file


def to_faebryk_t2_netlist(kicad_netlist: str | Path | list) -> T2Netlist:
    netlist = C_kicad_netlist_file.loads(kicad_netlist)

    components: dict[str, T2Netlist.Component] = {
        comp.ref: T2Netlist.Component(
            name=comp.ref,
            value=comp.value,
            properties={"footprint": comp.footprint}
            | {v.name: v.value for v in comp.propertys},
        )
        for comp in netlist.export.components.comps
    }

    t2_netlist = T2Netlist(
        nets=[
            T2Netlist.Net(
                properties={
                    "name": net.name,
                },
                vertices=[
                    T2Netlist.Net.Vertex(
                        component=components[node.ref],
                        pin=node.pin,
                    )
                    for node in net.nodes
                ],
            )
            for net in netlist.export.nets.nets
        ],
        comps=list(components.values()),
    )

    return t2_netlist
