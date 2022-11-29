# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

"""
This file contains a faebryk sample.
Faebryk samples demonstrate the usage by building example systems.
This particular sample creates a netlist with some resistors and a nand ic 
    with no specific further purpose or function.
Thus this is a netlist sample.
Netlist samples can be run directly.
The netlist is printed to stdout.
"""
import logging

# library imports
from faebryk.library.core import Module
from faebryk.library.graph import make_graph_from_nodes
from faebryk.library.library.components import TI_CD4011BE, Resistor
from faebryk.library.library.footprints import SMDTwoPin, can_attach_to_footprint
from faebryk.library.library.interfaces import ElectricPower
from faebryk.library.library.parameters import Constant
from faebryk.libs.experiments.buildutil import export_graph

logger = logging.getLogger("main")


def main():
    logging.basicConfig(level=logging.INFO)

    logger.info("Running experiment")

    # power
    class Battery(Module):
        class _IFS(Module.IFS()):
            power = ElectricPower()

        def __init__(self) -> None:
            super().__init__()
            self.IFs = Battery._IFS(self)

    battery = Battery()

    # functional components
    resistor1 = Resistor(Constant(100))
    resistor2 = Resistor(Constant(100))
    cd4011 = TI_CD4011BE()

    # aliases
    vcc = battery.IFs.power.NODEs.hv
    gnd = battery.IFs.power.NODEs.lv
    high = vcc
    low = gnd

    # connections
    r1it = iter(resistor1.IFs.get_all())
    r2it = iter(resistor2.IFs.get_all())
    next(r1it).connect(vcc).connect(next(r2it))
    next(r1it).connect(gnd).connect(next(r2it))
    cd4011.NODEs.nands[0].IFs.inputs[0].connect(high)
    cd4011.NODEs.nands[0].IFs.inputs[1].connect(low)
    cd4011.IFs.power.connect(battery.IFs.power)

    # make kicad netlist exportable (packages, pinmaps)
    for r in [resistor1, resistor2]:
        r.get_trait(can_attach_to_footprint).attach(SMDTwoPin(SMDTwoPin.Type._0805))

    comps = [
        battery,
        resistor1,
        resistor2,
        cd4011,
    ]

    G = make_graph_from_nodes(comps)
    # t1_ = make_t1_netlist_from_graph(make_graph_from_components(comps))

    # netlist = from_faebryk_t2_netlist(make_t2_netlist_from_t1(t1_))
    # assert netlist is not None

    # export_netlist(netlist)
    export_graph(G, show=True)


if __name__ == "__main__":
    main()
