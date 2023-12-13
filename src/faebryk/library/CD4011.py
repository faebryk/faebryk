# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

from faebryk.library.Constant import Constant
from faebryk.library.has_simple_value_representation_defined import (
    has_simple_value_representation_defined,
)
from faebryk.library.Logic74xx import Logic74xx
from faebryk.library.LogicGate import ElectricNAND


class CD4011(Logic74xx):
    def __init__(self):
        super().__init__(
            [lambda: ElectricNAND(input_cnt=Constant(2)) for _ in range(4)]
        )

        self.add_trait(has_simple_value_representation_defined("cd4011"))
