# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging

from faebryk.core.core import Module
from faebryk.library.can_attach_to_footprint_via_pinmap import (
    can_attach_to_footprint_via_pinmap,
)
from faebryk.library.can_be_decoupled import can_be_decoupled
from faebryk.library.Constant import Constant
from faebryk.library.Electrical import Electrical
from faebryk.library.ElectricLogic import ElectricLogic
from faebryk.library.ElectricPower import ElectricPower
from faebryk.library.has_datasheet_defined import has_datasheet_defined
from faebryk.library.has_designator_prefix_defined import has_designator_prefix_defined
from faebryk.library.has_single_electric_reference_defined import (
    has_single_electric_reference_defined,
)
from faebryk.library.I2C import I2C
from faebryk.library.MultiSPI import MultiSPI
from faebryk.library.SWD import SWD
from faebryk.library.UART_Base import UART_Base
from faebryk.library.USB2_0 import USB2_0
from faebryk.libs.units import P
from faebryk.libs.util import times

logger = logging.getLogger(__name__)


class RP2040(Module):
    def __init__(self) -> None:
        super().__init__()

        class _NODEs(Module.NODES()): ...

        self.NODEs = _NODEs(self)

        class _IFs(Module.IFS()):
            io_vdd = ElectricPower()
            adc_vdd = ElectricPower()
            core_vdd = ElectricPower()
            vreg_in = ElectricPower()
            vreg_out = ElectricPower()
            power_vusb = ElectricPower()
            gpio = times(30, Electrical)
            run = ElectricLogic()
            usb = USB2_0()
            qspi = MultiSPI(data_lane_count=4)
            xin = Electrical()
            xout = Electrical()
            test = Electrical()
            swd = SWD()
            # TODO: these peripherals and more can be mapped to different pins
            i2c = I2C()
            uart = UART_Base()

        self.IFs = _IFs(self)

        class _PARAMs(Module.PARAMS()): ...

        self.PARAMs = _PARAMs(self)

        # decouple power rails and connect GNDs toghether
        gnd = self.IFs.io_vdd.IFs.lv
        for pwrrail in [
            self.IFs.io_vdd,
            self.IFs.adc_vdd,
            self.IFs.core_vdd,
            self.IFs.vreg_in,
            self.IFs.vreg_out,
            self.IFs.usb.IFs.usb_if.IFs.buspower,
        ]:
            pwrrail.IFs.lv.connect(gnd)
            pwrrail.get_trait(can_be_decoupled).decouple()

        self.add_trait(has_single_electric_reference_defined(self.IFs.io_vdd))

        self.add_trait(has_designator_prefix_defined("U"))

        self.add_trait(
            has_datasheet_defined(
                "https://datasheets.raspberrypi.com/rp2040/rp2040-datasheet.pdf"
            )
        )

        # set parameters
        self.IFs.vreg_out.PARAMs.voltage.merge(Constant(1.1 * P.V))
        self.IFs.io_vdd.PARAMs.voltage.merge(Constant(3.3 * P.V))
        # TODO: self.IFs.io_vdd.PARAMs.voltage.merge(Range(1.8*P.V, 3.63*P.V))

        self.add_trait(
            can_attach_to_footprint_via_pinmap(
                {
                    "1": self.IFs.io_vdd.IFs.hv,
                    "2": self.IFs.gpio[0],
                    "3": self.IFs.gpio[1],
                    "4": self.IFs.gpio[2],
                    "5": self.IFs.gpio[3],
                    "6": self.IFs.gpio[4],
                    "7": self.IFs.gpio[5],
                    "8": self.IFs.gpio[6],
                    "9": self.IFs.gpio[7],
                    "10": self.IFs.io_vdd.IFs.hv,
                    "11": self.IFs.gpio[8],
                    "12": self.IFs.gpio[9],
                    "13": self.IFs.gpio[10],
                    "14": self.IFs.gpio[11],
                    "15": self.IFs.gpio[12],
                    "16": self.IFs.gpio[13],
                    "17": self.IFs.gpio[14],
                    "18": self.IFs.gpio[15],
                    "19": self.IFs.xin,
                    "20": self.IFs.xout,
                    "21": self.IFs.test,
                    "22": self.IFs.io_vdd.IFs.hv,
                    "23": self.IFs.core_vdd.IFs.hv,
                    "24": self.IFs.swd.IFs.clk.IFs.signal,
                    "25": self.IFs.swd.IFs.dio.IFs.signal,
                    "26": self.IFs.run.IFs.signal,
                    "27": self.IFs.gpio[16],
                    "28": self.IFs.gpio[17],
                    "29": self.IFs.gpio[18],
                    "30": self.IFs.gpio[19],
                    "31": self.IFs.gpio[20],
                    "32": self.IFs.gpio[21],
                    "33": self.IFs.io_vdd.IFs.hv,
                    "34": self.IFs.gpio[22],
                    "35": self.IFs.gpio[23],
                    "36": self.IFs.gpio[24],
                    "37": self.IFs.gpio[25],
                    "38": self.IFs.gpio[26],
                    "39": self.IFs.gpio[27],
                    "40": self.IFs.gpio[28],
                    "41": self.IFs.gpio[29],
                    "42": self.IFs.io_vdd.IFs.hv,
                    "43": self.IFs.adc_vdd.IFs.hv,
                    "44": self.IFs.vreg_in.IFs.hv,
                    "45": self.IFs.vreg_out.IFs.hv,
                    "46": self.IFs.usb.IFs.usb_if.IFs.d.IFs.n,
                    "47": self.IFs.usb.IFs.usb_if.IFs.d.IFs.p,
                    "48": self.IFs.usb.IFs.usb_if.IFs.buspower.IFs.hv,
                    "49": self.IFs.io_vdd.IFs.hv,
                    "50": self.IFs.core_vdd.IFs.hv,
                    "51": self.IFs.qspi.IFs.data[3].IFs.signal,
                    "52": self.IFs.qspi.IFs.clk.IFs.signal,
                    "53": self.IFs.qspi.IFs.data[0].IFs.signal,
                    "54": self.IFs.qspi.IFs.data[2].IFs.signal,
                    "55": self.IFs.qspi.IFs.data[1].IFs.signal,
                    "56": self.IFs.qspi.IFs.cs.IFs.signal,
                    "57": self.IFs.io_vdd.IFs.lv,
                }
            )
        )
