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
"""
import logging

import typer
from faebryk.core.core import Module, Parameter
from faebryk.core.util import get_all_nodes, specialize_interface, specialize_module
from faebryk.exporters.netlist.graph import attach_nets_and_kicad_info
from faebryk.exporters.netlist.kicad.netlist_kicad import from_faebryk_t2_netlist
from faebryk.exporters.netlist.netlist import make_t2_netlist_from_graph
from faebryk.exporters.visualize.graph import render_matrix
from faebryk.library.can_attach_to_footprint import can_attach_to_footprint
from faebryk.library.can_attach_to_footprint_via_pinmap import (
    can_attach_to_footprint_via_pinmap,
)
from faebryk.library.Constant import Constant
from faebryk.library.Electrical import Electrical
from faebryk.library.ElectricLogic import ElectricLogic, can_be_pulled
from faebryk.library.ElectricPower import ElectricPower
from faebryk.library.has_simple_value_representation_defined import (
    has_simple_value_representation_defined,
)
from faebryk.library.KicadFootprint import KicadFootprint
from faebryk.library.LED import LED
from faebryk.library.Logic import Logic
from faebryk.library.LogicGate import NAND, can_logic_nand
from faebryk.library.Resistor import Resistor
from faebryk.library.SMDTwoPin import SMDTwoPin
from faebryk.library.Switch import Switch
from faebryk.library.TBD import TBD
from faebryk.library.TI_CD4011BE import TI_CD4011BE
from faebryk.libs.experiments.buildutil import export_netlist
from faebryk.libs.logging import setup_basic_logging
from faebryk.libs.util import times

logger = logging.getLogger(__name__)


class Battery(Module):
    def __init__(self) -> None:
        super().__init__()

        class IFS(Module.IFS()):
            power = ElectricPower()

        self.IFs = IFS(self)
        self.voltage: Parameter = TBD()


class PowerSource(Module):
    def __init__(self) -> None:
        super().__init__()

        class IFS(Module.IFS()):
            power_out = ElectricPower()

        self.IFs = IFS(self)


class XOR(Module):
    def __init__(
        self,
    ):
        super().__init__()

        class IFS(Module.IFS()):
            inputs = times(2, Logic)
            output = Logic()

        self.IFs = IFS(self)

    def xor(self, in1: Logic, in2: Logic):
        self.IFs.inputs[0].connect(in1)
        self.IFs.inputs[1].connect(in2)
        return self.IFs.output


class XOR_with_NANDS(XOR):
    def __init__(
        self,
    ):
        super().__init__()

        class NODES(Module.NODES()):
            nands = times(4, lambda: NAND(Constant(2)))

        self.NODEs = NODES(self)

        A = self.IFs.inputs[0]
        B = self.IFs.inputs[1]

        G = self.NODEs.nands
        Q = self.IFs.output

        # ~(a&b)
        q0 = G[0].get_trait(can_logic_nand).nand(A, B)
        # ~(a&~b)
        q1 = G[1].get_trait(can_logic_nand).nand(A, q0)
        # ~(~a&b)
        q2 = G[2].get_trait(can_logic_nand).nand(B, q0)
        # (a&~b) o| (~a&b)
        q3 = G[3].get_trait(can_logic_nand).nand(q1, q2)

        Q.connect(q3)


def App():
    # levels
    on = Logic()
    off = Logic()

    # power
    power_source = PowerSource()

    # alias
    power = power_source.IFs.power_out
    gnd = Electrical().connect(power.IFs.lv)

    # logic
    logic_in = Logic()
    logic_out = Logic()

    xor = XOR()
    logic_out.connect(xor.xor(logic_in, on))

    # led
    current_limiting_resistor = Resistor()
    led = LED()
    led.IFs.cathode.connect_via(current_limiting_resistor, gnd)

    # application
    switch = Switch(Logic)()

    logic_in.connect_via(switch, on)

    e_in = specialize_interface(logic_in, ElectricLogic())
    pull_down_resistor = e_in.get_trait(can_be_pulled).pull(up=False)

    e_out = specialize_interface(logic_out, ElectricLogic())
    e_out.IFs.signal.connect(led.IFs.anode)

    specialize_interface(on, ElectricLogic()).connect_to_electric(power.IFs.hv, power)
    specialize_interface(off, ElectricLogic()).connect_to_electric(power.IFs.lv, power)

    nxor = specialize_module(xor, XOR_with_NANDS())

    battery = specialize_module(power_source, Battery())

    el_switch = specialize_module(switch, Switch(ElectricLogic)())
    e_switch = Switch(Electrical)()
    # TODO make switch generic to remove the asserts
    for e, el in zip(e_switch.IFs.unnamed, el_switch.IFs.unnamed):
        assert isinstance(el, ElectricLogic)
        assert isinstance(e, Electrical)
        el.connect_to_electric(e, battery.IFs.power)

    # build graph
    app = Module()
    app.NODEs.components = [
        led,
        current_limiting_resistor,
        switch,
        battery,
        e_switch,
    ]

    # parametrizing
    pull_down_resistor.PARAMs.resistance.merge(Constant(100e3))

    for node in get_all_nodes(app):
        if isinstance(node, Battery):
            node.voltage = Constant(5)

        if isinstance(node, LED):
            node.PARAMs.forward_voltage.merge(Constant(2.4))
            node.PARAMs.max_current.merge(Constant(0.020))

    current_limiting_resistor.PARAMs.resistance.merge(
        led.get_needed_series_resistance_for_current_limit(battery.voltage)
    )

    # packaging
    e_switch.get_trait(can_attach_to_footprint).attach(
        KicadFootprint.with_simple_names("Button_Switch_SMD:Panasonic_EVQPUJ_EVQPUA", 2)
    )
    for node in get_all_nodes(app):
        if isinstance(node, Battery):
            node.add_trait(
                can_attach_to_footprint_via_pinmap(
                    {"1": node.IFs.power.IFs.hv, "2": node.IFs.power.IFs.lv}
                )
            ).attach(
                KicadFootprint.with_simple_names(
                    "Battery:BatteryHolder_ComfortableElectronic_CH273-2450_1x2450", 2
                )
            )
            node.add_trait(has_simple_value_representation_defined("B"))

        if isinstance(node, Resistor):
            node.get_trait(can_attach_to_footprint).attach(
                SMDTwoPin(SMDTwoPin.Type._0805)
            )

        if isinstance(node, LED):
            node.add_trait(
                can_attach_to_footprint_via_pinmap(
                    {"1": node.IFs.anode, "2": node.IFs.cathode}
                )
            ).attach(SMDTwoPin(SMDTwoPin.Type._0805))

    # packages single nands as explicit IC
    nand_ic = TI_CD4011BE()
    for ic_nand, xor_nand in zip(nand_ic.NODEs.gates, nxor.NODEs.nands):
        specialize_module(xor_nand, ic_nand)

    app.NODEs.nand_ic = nand_ic

    # for visualization
    helpers = [nxor, xor, e_out]

    return app, helpers


def main(make_graph: bool = True):
    logger.info("Building app")
    app, helpers = App()

    # export
    logger.info("Make graph")
    G = app.get_graph()

    logger.info("Make netlist")
    attach_nets_and_kicad_info(G)
    t2 = make_t2_netlist_from_graph(G)
    netlist = from_faebryk_t2_netlist(t2)

    export_netlist(netlist)

    if make_graph:
        logger.info("Make render")
        render_matrix(
            G.G,
            nodes_rows=[
                [app.NODEs.nand_ic, app.NODEs.components[0], *helpers],
            ],
            depth=1,
            show_full=False,
            show_non_sum=False,
        ).show()
        # export_graph(G.G, False)


if __name__ == "__main__":
    setup_basic_logging()
    logger.info("Running experiment")

    typer.run(main)
