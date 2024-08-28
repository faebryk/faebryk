# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging

from faebryk.core.core import Module
from faebryk.exporters.pcb.layout.absolute import LayoutAbsolute
from faebryk.exporters.pcb.layout.extrude import LayoutExtrude
from faebryk.exporters.pcb.layout.typehierarchy import LayoutTypeHierarchy
from faebryk.library.Button import Button
from faebryk.library.Capacitor import Capacitor
from faebryk.library.Constant import Constant
from faebryk.library.Crystal import Crystal
from faebryk.library.Crystal_Oscillator import Crystal_Oscillator
from faebryk.library.has_pcb_layout_defined import has_pcb_layout_defined
from faebryk.library.has_pcb_position import has_pcb_position
from faebryk.library.LDO import LDO
from faebryk.library.LED import LED
from faebryk.library.PoweredLED import PoweredLED
from faebryk.library.Resistor import Resistor
from faebryk.library.RP2040 import RP2040
from faebryk.library.SPIFlash import SPIFlash
from faebryk.library.USB2_0 import USB2_0
from faebryk.libs.brightness import TypicalLuminousIntensity
from faebryk.libs.units import P
from faebryk.libs.util import times

logger = logging.getLogger(__name__)


class RP2040_Reference_Design(Module):
    def __init__(self) -> None:
        super().__init__()

        # ----------------------------------------
        #     modules, interfaces, parameters
        # ----------------------------------------
        class _IFs(Module.IFS()):
            usb = USB2_0()

        self.IFs = _IFs(self)

        class _NODES(Module.NODES()):
            rp2040 = RP2040()
            flash = SPIFlash()
            led = PoweredLED()
            usb_current_limmit_resistor = times(2, Resistor)
            reset_button = Button()
            boot_button = Button()
            boot_resistor = Resistor()
            ldo = LDO()
            crystal_oscillator = Crystal_Oscillator()
            oscilator_resistor = Resistor()
            # TODO: add voltage divider with switch
            # TODO: add optional LM4040 voltage reference or voltage divider

        self.NODEs = _NODES(self)

        class _PARAMs(Module.PARAMS()): ...

        self.PARAMs = _PARAMs(self)

        # ----------------------------------------
        #                aliasess
        # ----------------------------------------
        power_3v3 = self.NODEs.ldo.IFs.power_out
        power_5v = self.NODEs.ldo.IFs.power_in
        power_vbus = self.IFs.usb.IFs.usb_if.IFs.buspower
        gnd = power_vbus.IFs.lv
        # ----------------------------------------
        #            parametrization
        # ----------------------------------------
        self.NODEs.ldo.PARAMs.output_voltage.merge(Constant(3.3 * P.V))
        self.NODEs.ldo.PARAMs.output_current.merge(Constant(600 * P.mA))

        self.NODEs.flash.PARAMs.memory_size.merge(Constant(16 * P.Mbit))

        self.NODEs.crystal_oscillator.NODEs.crystal.PARAMs.frequency.merge(
            Constant(12 * P.Mhertz)
        )
        self.NODEs.crystal_oscillator.NODEs.crystal.PARAMs.load_impedance.merge(
            Constant(10 * P.pF)
        )
        # for cap in self.NODEs.crystal_oscillator.NODEs.capacitors:
        #    cap.PARAMs.capacitance.merge(Constant(15e-12))  # TODO: remove?
        self.NODEs.oscilator_resistor.PARAMs.resistance.merge(Constant(1 * P.kohm))

        self.NODEs.led.NODEs.led.PARAMs.color.merge(LED.Color.GREEN)
        self.NODEs.led.NODEs.led.PARAMs.brightness.merge(
            TypicalLuminousIntensity.APPLICATION_LED_INDICATOR_INSIDE.value.value
        )
        # TODO: remove: #poweredled voltage merge issue
        self.NODEs.led.IFs.power.PARAMs.voltage.merge(power_3v3.PARAMs.voltage)

        self.NODEs.usb_current_limmit_resistor[0].PARAMs.resistance.merge(
            Constant(27 * P.ohm)
        )
        self.NODEs.usb_current_limmit_resistor[1].PARAMs.resistance.merge(
            Constant(27 * P.ohm)
        )

        # ----------------------------------------
        #              connections
        # ----------------------------------------
        power_vbus.connect(power_5v)

        # connect rp2040 power rails
        for pwrrail in [
            self.NODEs.rp2040.IFs.io_vdd,
            self.NODEs.rp2040.IFs.adc_vdd,
            self.NODEs.rp2040.IFs.vreg_in,
        ]:
            pwrrail.connect(power_3v3)

        self.NODEs.rp2040.IFs.vreg_out.connect(self.NODEs.rp2040.IFs.core_vdd)

        # connect flash
        self.NODEs.flash.IFs.spi.connect(self.NODEs.rp2040.IFs.qspi)
        self.NODEs.flash.IFs.power.connect(power_3v3)

        # connect led
        self.NODEs.rp2040.IFs.gpio[25].connect_via(self.NODEs.led, gnd)

        # connect usb
        self.IFs.usb.IFs.usb_if.IFs.d.IFs.p.connect_via(
            self.NODEs.usb_current_limmit_resistor[0],
            self.NODEs.rp2040.IFs.usb.IFs.usb_if.IFs.d.IFs.p,
        )
        self.IFs.usb.IFs.usb_if.IFs.d.IFs.n.connect_via(
            self.NODEs.usb_current_limmit_resistor[1],
            self.NODEs.rp2040.IFs.usb.IFs.usb_if.IFs.d.IFs.n,
        )

        # crystal oscillator
        self.NODEs.rp2040.IFs.xin.connect_via(
            [self.NODEs.crystal_oscillator, self.NODEs.oscilator_resistor],
            self.NODEs.rp2040.IFs.xout,
        )
        gnd.connect(self.NODEs.crystal_oscillator.IFs.power.IFs.lv)

        # buttons
        self.NODEs.rp2040.IFs.qspi.IFs.cs.IFs.signal.connect_via(
            [self.NODEs.boot_resistor, self.NODEs.boot_button], gnd
        )
        self.NODEs.boot_resistor.PARAMs.resistance.merge(Constant(1 * P.kohm))
        self.NODEs.rp2040.IFs.run.IFs.signal.connect_via(self.NODEs.reset_button, gnd)

        # ----------------------------------------
        # specify components with footprints

        # pcb layout
        Point = has_pcb_position.Point
        L = has_pcb_position.layer_type
        self.add_trait(
            has_pcb_layout_defined(
                layout=LayoutTypeHierarchy(
                    layouts=[
                        LayoutTypeHierarchy.Level(
                            mod_type=RP2040,
                            layout=LayoutAbsolute(
                                Point((0, 0, 0, L.NONE)),
                            ),
                        ),
                        LayoutTypeHierarchy.Level(
                            mod_type=LDO,
                            layout=LayoutAbsolute(Point((0, 14, 0, L.NONE))),
                        ),
                        LayoutTypeHierarchy.Level(
                            mod_type=Button,
                            layout=LayoutExtrude(
                                base=Point((-1.75, -11.5, 0, L.NONE)),
                                vector=(3.5, 0, 90),
                            ),
                        ),
                        LayoutTypeHierarchy.Level(
                            mod_type=SPIFlash,
                            layout=LayoutAbsolute(
                                Point((-1.95, -6.5, 0, L.NONE)),
                            ),
                        ),
                        LayoutTypeHierarchy.Level(
                            mod_type=PoweredLED,
                            layout=LayoutAbsolute(
                                Point((6.5, -1.5, 270, L.NONE)),
                            ),
                            children_layout=LayoutTypeHierarchy(
                                layouts=[
                                    LayoutTypeHierarchy.Level(
                                        mod_type=LED,
                                        layout=LayoutAbsolute(
                                            Point((0, 0, 0, L.NONE)),
                                        ),
                                    ),
                                    LayoutTypeHierarchy.Level(
                                        mod_type=Resistor,
                                        layout=LayoutAbsolute(
                                            Point((-2.75, 0, 180, L.NONE))
                                        ),
                                    ),
                                ]
                            ),
                        ),
                        LayoutTypeHierarchy.Level(
                            mod_type=Crystal_Oscillator,
                            layout=LayoutAbsolute(
                                Point((0, 7, 0, L.NONE)),
                            ),
                            children_layout=LayoutTypeHierarchy(
                                layouts=[
                                    LayoutTypeHierarchy.Level(
                                        mod_type=Crystal,
                                        layout=LayoutAbsolute(
                                            Point((0, 0, 0, L.NONE)),
                                        ),
                                    ),
                                    LayoutTypeHierarchy.Level(
                                        mod_type=Capacitor,
                                        layout=LayoutExtrude(
                                            base=Point((-3, 0, 90, L.NONE)),
                                            vector=(0, 6, 180),
                                            dynamic_rotation=True,
                                        ),
                                    ),
                                ]
                            ),
                        ),
                        LayoutTypeHierarchy.Level(
                            mod_type=Resistor,
                            layout=LayoutExtrude(
                                base=Point((0.75, -6, 0, L.NONE)),
                                vector=(1.25, 0, 270),
                            ),
                        ),
                    ]
                )
            )
        )
