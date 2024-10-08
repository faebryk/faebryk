# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging

import faebryk.library._F as F
from faebryk.core.module import Module
from faebryk.libs.library import L
from faebryk.libs.units import P, Quantity

logger = logging.getLogger(__name__)


class UART_RS485(Module):
    power: F.ElectricPower
    uart: F.UART_Base
    rs485: F.RS485
    read_enable: F.ElectricLogic
    write_enable: F.ElectricLogic

    max_data_rate: F.TBD[Quantity]
    gpio_voltage: F.TBD[Quantity]

    def __preinit__(self):
        self.power.voltage.merge(F.Range(3.3 * P.V, 5.0 * P.V))
        self.power.decoupled.decouple()

    designator_prefix = L.f_field(F.has_designator_prefix_defined)("U")
