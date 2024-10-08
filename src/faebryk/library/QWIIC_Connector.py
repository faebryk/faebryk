# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging

import faebryk.library._F as F
from faebryk.core.module import Module
from faebryk.libs.library import L

logger = logging.getLogger(__name__)


class QWIIC_Connector(Module):
    power: F.ElectricPower
    i2c: F.I2C

    designator_prefix = L.f_field(F.has_designator_prefix_defined)("J")
