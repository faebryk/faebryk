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

import typer

from faebryk.exporters.netlist.graph import make_t1_netlist_from_graph
from faebryk.exporters.netlist.kicad.netlist_kicad import from_faebryk_t2_netlist
from faebryk.exporters.netlist.netlist import make_t2_netlist_from_t1

# library imports
from faebryk.library.core import Module
from faebryk.library.library.components import TI_CD4011BE, Resistor
from faebryk.library.library.footprints import SMDTwoPin, can_attach_to_footprint
from faebryk.library.library.interfaces import Electrical, ElectricPower
from faebryk.library.library.parameters import Constant
from faebryk.libs.experiments.buildutil import export_graph, export_netlist

logger = logging.getLogger(__name__)


def main():
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
    vcc = Electrical()
    gnd = Electrical()
    high = vcc
    low = gnd

    # connections
    r1it = iter(resistor1.IFs.get_all())
    r2it = iter(resistor2.IFs.get_all())
    for it in [
        r1it,
        r2it,
    ]:
        next(it).connect(vcc)
        next(it).connect(gnd)
    cd4011.NODEs.nands[0].IFs.inputs[0].connect(high)
    cd4011.NODEs.nands[0].IFs.inputs[1].connect(low)
    cd4011.IFs.power.connect(battery.IFs.power)

    vcc.connect(battery.IFs.power.NODEs.hv)
    gnd.connect(battery.IFs.power.NODEs.lv)

    # make netlist exportable (packages, pinmaps)
    for r in [
        resistor1,
        resistor2,
    ]:
        r.get_trait(can_attach_to_footprint).attach(SMDTwoPin(SMDTwoPin.Type._0805))

    # Export
    app = Module()
    app.NODEs.components = [battery, resistor1, resistor2, cd4011]
    G = app.get_graph()

    t1 = make_t1_netlist_from_graph(G)
    t2 = make_t2_netlist_from_t1(t1)
    netlist = from_faebryk_t2_netlist(t2)

    export_graph(G.G, True)
    export_netlist(netlist)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    logger.info("Running experiment")

    typer.run(main)
