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

    class ConstraintConsume(Constraint):
        ...

    class ConstraintConsumeCurrent(ConstraintConsume):
        def __init__(self, current: Parameter) -> None:
            self.current = current

    class ConstraintConsumeVoltage(ConstraintConsume):
        def __init__(
            self, voltage: Parameter, tolerance: Parameter = Constant(0)
        ) -> None:
            self.voltage = voltage
            self.tolerance = tolerance

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
