# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

from typing import Sequence

from faebryk.core.core import ModuleInterface, Parameter
from faebryk.library.Capacitor import Capacitor
from faebryk.library.Constant import Constant
from faebryk.library.Electrical import Electrical
from faebryk.library.Power import Power


class ElectricPower(Power):
    class Constraint:
        ...

    class ConstraintCurrent(Constraint):
        def __init__(self, current: Parameter) -> None:
            self.current = current

    class ConstraintVoltage(Constraint):
        def __init__(self, voltage: Parameter) -> None:
            self.voltage = voltage

    def __init__(self) -> None:
        super().__init__()

        class NODES(Power.NODES()):
            hv = Electrical()
            lv = Electrical()

        self.NODEs = NODES(self)

        self.constraints: Sequence[ElectricPower.Constraint] = []

    def _on_connect(self, other: ModuleInterface) -> None:
        super()._on_connect(other)

        if isinstance(other, type(self)):
            self.NODEs.hv.connect(other.NODEs.hv)
            self.NODEs.lv.connect(other.NODEs.lv)

    def decouple(self, capacitor: Capacitor):
        self.NODEs.hv.connect_via(capacitor, self.NODEs.lv)

    def add_constraint(self, *constraint: Constraint):
        self.constraints.extend(list(constraint))

    def connect(self, other: ModuleInterface):
        super().connect(other)
        if not isinstance(other, ElectricPower):
            return

        constraints = set(self.constraints + other.constraints)

        # checks if voltages compatible
        Parameter.resolve_all(
            {
                c.voltage
                for c in constraints
                if isinstance(c, ElectricPower.ConstraintVoltage)
            }
        )
