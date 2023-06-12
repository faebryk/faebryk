# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

"""
This file contains a faebryk sample.
Faebryk samples demonstrate the usage by building example systems.
This particular sample creates a netlist with an led and a nand ic 
    that creates some logic. 
The goal of this sample is to show how faebryk can be used to iteratively
    expand the specifics of a design in multiple steps.
Thus this is a netlist sample.
Netlist samples can be run directly.
The netlist is printed to stdout.
"""
import logging

import typer

from faebryk.exporters.netlist.graph import make_t1_netlist_from_graph
from faebryk.exporters.netlist.kicad.netlist_kicad import from_faebryk_t2_netlist
from faebryk.exporters.netlist.netlist import make_t2_netlist_from_t1
from faebryk.library.core import Module, Node, Parameter
from faebryk.library.kicad import KicadFootprint
from faebryk.library.library.components import LED, NAND, TI_CD4011BE, Resistor, Switch
from faebryk.library.library.footprints import (
    SMDTwoPin,
    can_attach_to_footprint,
    can_attach_to_footprint_via_pinmap,
)
from faebryk.library.library.interfaces import Electrical, ElectricPower
from faebryk.library.library.parameters import TBD, Constant
from faebryk.library.trait_impl.component import has_defined_type_description
from faebryk.library.traits.component import has_footprint
from faebryk.library.util import get_all_nodes, zip_connect_modules
from faebryk.libs.experiments.buildutil import export_graph, export_netlist

logger = logging.getLogger(__name__)


def main():
    # levels
    high = Electrical()
    low = Electrical()

    # power
    class Battery(Node):
        def __init__(self) -> None:
            super().__init__()

            class _IFs(Node.GraphInterfacesCls()):
                power = ElectricPower()

            self.IFs = _IFs(self)
            self.voltage: Parameter = TBD()

    battery = Battery()

    # alias
    gnd = battery.IFs.power.NODEs.lv
    power = battery.IFs.power

    # logic
    nands = [NAND(2) for _ in range(2)]
    nands[0].IFs.inputs[1].connect(low)
    nands[1].IFs.inputs[0].connect(nands[0].IFs.output)
    nands[1].IFs.inputs[1].connect(low)
    logic_in = nands[0].IFs.inputs[0]
    logic_out = nands[1].IFs.output

    # led
    current_limiting_resistor = Resistor(resistance=TBD())
    led = LED()
    led.IFs.cathode.connect_via(current_limiting_resistor, gnd)

    # application
    switch = Switch()
    pull_down_resistor = Resistor(TBD())

    logic_in.connect_via(pull_down_resistor, low)
    logic_in.connect_via(switch, high)
    logic_out.connect(led.IFs.anode)

    high.connect(power.NODEs.hv)
    low.connect(power.NODEs.lv)

    # build graph
    app = Module()
    app.NODEs.components = [
        led,
        pull_down_resistor,
        current_limiting_resistor,
        switch,
        battery,
    ]
    app.NODEs.nands = nands

    # parametrizing
    pull_down_resistor.set_resistance(Constant(100_000))

    for node in get_all_nodes(app):
        if isinstance(node, Battery):
            node.voltage = Constant(5)

        if isinstance(node, LED):
            node.set_forward_parameters(
                voltage_V=Constant(2.4), current_A=Constant(0.020)
            )

    assert isinstance(battery.voltage, Constant)
    current_limiting_resistor.set_resistance(
        led.get_trait(
            LED.has_calculatable_needed_series_resistance
        ).get_needed_series_resistance_ohm(battery.voltage.value)
    )

    # packaging
    for node in get_all_nodes(app):
        if isinstance(node, Battery):
            node.add_trait(
                can_attach_to_footprint_via_pinmap(
                    {"1": node.IFs.power.NODEs.hv, "2": node.IFs.power.NODEs.lv}
                )
            ).attach(
                KicadFootprint.with_simple_names(
                    "BatteryHolder_ComfortableElectronic_CH273-2450_1x2450", 2
                )
            )
            node.add_trait(has_defined_type_description("B"))

        if isinstance(node, Resistor):
            node.get_trait(can_attach_to_footprint).attach(
                SMDTwoPin(SMDTwoPin.Type._0805)
            )

        if isinstance(node, Switch):
            node.get_trait(can_attach_to_footprint).attach(
                KicadFootprint.with_simple_names("Panasonic_EVQPUJ_EVQPUA", 2)
            )

        if isinstance(node, LED):
            node.add_trait(
                can_attach_to_footprint_via_pinmap(
                    {"1": node.IFs.anode, "2": node.IFs.cathode}
                )
            ).attach(SMDTwoPin(SMDTwoPin.Type._0805))

    # packages single nands as explicit IC
    nand_ic = TI_CD4011BE()
    zip_connect_modules(nand_ic.NODEs.nands, nands)
    app.NODEs.nand_ic = nand_ic
    for nand in nands:
        nand.del_trait(has_footprint)

    # export
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
