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
from faebryk.library.core import Module, Parameter
from faebryk.library.kicad import KicadFootprint
from faebryk.library.library.components import LED, MOSFET, Resistor, Switch
from faebryk.library.library.footprints import (
    SMDTwoPin,
    can_attach_to_footprint,
    can_attach_to_footprint_via_pinmap,
)
from faebryk.library.library.interfaces import Electrical
from faebryk.library.library.parameters import TBD, Constant
from faebryk.library.util import get_all_nodes
from faebryk.libs.experiments.buildutil import export_graph, export_netlist

logger = logging.getLogger(__name__)


def main():
    # power
    class Battery(Module):
        def __init__(self) -> None:
            super().__init__()

            class _IFs(Module.IFS()):
                power = Power()

            self.IFs = _IFs(self)
            self.voltage: Parameter = TBD()

    class LED_Indicator(Module):
        def __init__(self) -> None:
            super().__init__()

            class _IFS(Module.IFS()):
                input_power = Power()
                input_control = Electrical()

            class _CMPS(Module.NODES()):
                led = LED()
                current_limiting_resistor = Resistor(TBD())
                switch = MOSFET()

            self.IFs = _IFS(self)
            self.CMPs = _CMPS(self)

            # fabric
            # TODO
            self.CMPs.led.IFs.cathode.connect_via(
                self.CMPs.current_limiting_resistor, self.IFs.input_power.IFs.lv
            )
            self.CMPs.led.IFs.anode.connect(self.CMPs.switch.IFs.drain)

            self.CMPs.switch.IFs.source.connect(self.IFs.input_power.IFs.hv)
            self.CMPs.switch.IFs.gate.connect(self.IFs.input_control)

    class LogicSwitch(Module):
        def __init__(self) -> None:
            super().__init__()

            class _IFS(Module.IFS()):
                input_power = Power()
                output_control = Electrical()

            class _CMPS(Module.NODES()):
                switch = Switch()
                pull_down_resistor = Resistor(TBD())

            self.IFs = _IFS(self)
            self.CMPs = _CMPS(self)

            # fabric
            self.IFs.input_power.IFs.hv.connect_via(
                self.CMPs.switch, self.IFs.output_control
            )
            self.IFs.input_power.IFs.lv.connect_via(
                self.CMPs.pull_down_resistor, self.IFs.output_control
            )

    class App(Module):
        def __init__(self) -> None:
            super().__init__()

            class _IFS(Module.IFS()):
                pass

            class _CMPS(Module.NODES()):
                battery = Battery()
                led_ind = LED_Indicator()
                switch = LogicSwitch()

            self.IFs = _IFS(self)
            self.CMPs = _CMPS(self)

            # fabric
            power = self.CMPs.battery.IFs.power

            power.connect(self.CMPs.led_ind.IFs.input_power)
            power.connect(self.CMPs.switch.IFs.input_power)
            self.CMPs.switch.IFs.output_control.connect(
                self.CMPs.led_ind.IFs.input_control
            )

    app = App()

    # parametrizing
    for node in get_all_nodes(app, order_types=[Battery, LED, LED_Indicator]):
        if isinstance(node, Battery):
            node.voltage = Constant(5)

        if isinstance(node, LED):
            node.set_forward_parameters(
                voltage_V=Constant(2.4), current_A=Constant(0.020)
            )

        if isinstance(node, LED_Indicator):
            assert isinstance(app.CMPs.battery.voltage, Constant)
            node.CMPs.current_limiting_resistor.set_resistance(
                node.CMPs.led.get_trait(
                    LED.has_calculatable_needed_series_resistance
                ).get_needed_series_resistance_ohm(app.CMPs.battery.voltage.value)
            )

        if isinstance(node, LogicSwitch):
            node.CMPs.pull_down_resistor.set_resistance(Constant(100_000))

    # packaging
    for node in get_all_nodes(app):
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

    # make graph
    G = app.get_graph()
    t1_ = make_t1_netlist_from_graph(G)

    netlist = from_faebryk_t2_netlist(make_t2_netlist_from_t1(t1_))
    assert netlist is not None

    export_netlist(netlist)
    export_graph(G.G, show=True)


# Boilerplate -----------------------------------------------------------------
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    logger.info("Running experiment")

    typer.run(main)
