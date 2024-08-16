# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging

from faebryk.core.core import Module
from faebryk.library.Button import Button
from faebryk.library.Constant import Constant
from faebryk.library.Crystal_Oscillator import Crystal_Oscillator
from faebryk.library.has_datasheet_defined import has_datasheet_defined
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
    """Minimal required design for the Raspberry Pi RP2040 microcontroller.
    Based on the official Raspberry Pi RP2040 hardware design guidlines"""

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
            crystal_oscilator = Crystal_Oscillator()
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

        self.NODEs.crystal_oscilator.NODEs.crystal.PARAMs.frequency.merge(
            Constant(12 * P.Mhertz)
        )
        self.NODEs.crystal_oscilator.NODEs.crystal.PARAMs.load_impedance.merge(
            Constant(10 * P.pF)
        )

        self.NODEs.flash.PARAMs.memory_size.merge(Constant(16 * P.Mbit))

        self.NODEs.led.NODEs.led.PARAMs.color.merge(LED.Color.GREEN)
        self.NODEs.led.NODEs.led.PARAMs.brightness.merge(
            TypicalLuminousIntensity.APPLICATION_LED_INDICATOR_INSIDE.value.value
        )

        self.NODEs.usb_current_limmit_resistor[0].PARAMs.resistance.merge(
            Constant(27 * P.ohm)
        )
        self.NODEs.usb_current_limmit_resistor[1].PARAMs.resistance.merge(
            Constant(27 * P.ohm)
        )

        # ----------------------------------------
        #              connections
        # ----------------------------------------
        self.NODEs.ldo.IFs.power_in.connect(power_5v)

        # connect rp2040 power rails
        for pwrrail in [
            self.NODEs.rp2040.IFs.io_vdd,
            self.NODEs.rp2040.IFs.adc_vdd,
            self.NODEs.rp2040.IFs.vreg_in,
            self.NODEs.rp2040.IFs.usb.IFs.usb_if.IFs.buspower,
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

        # crystal oscilator
        self.NODEs.rp2040.IFs.xin.connect_via(
            [self.NODEs.crystal_oscilator, self.NODEs.oscilator_resistor],
            self.NODEs.rp2040.IFs.xout,
        )
        gnd.connect(self.NODEs.crystal_oscilator.IFs.power.IFs.lv)

        # buttons
        self.NODEs.rp2040.IFs.qspi.IFs.cs.IFs.signal.connect_via(
            [self.NODEs.boot_resistor, self.NODEs.boot_button], gnd
        )
        self.NODEs.boot_resistor.PARAMs.resistance.merge(Constant(1 * k))
        self.NODEs.rp2040.IFs.run.IFs.signal.connect_via(self.NODEs.reset_button, gnd)

        self.add_trait(
            has_datasheet_defined(
                "https://datasheets.raspberrypi.com/rp2040/hardware-design-with-rp2040.pdf"
            )
        )
