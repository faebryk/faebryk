# This file is part of the faebryk project
# SPDX-License-Identifier: MIT


from faebryk.core.core import ModuleInterface
from faebryk.library.can_be_decoupled_defined import can_be_decoupled_defined
from faebryk.library.can_be_surge_protected_defined import (
    can_be_surge_protected_defined,
)
from faebryk.library.Electrical import Electrical
from faebryk.library.Power import Power
from faebryk.library.Range import Range
from faebryk.library.TBD import TBD


class can_be_decoupled_power(can_be_decoupled_defined):
    def __init__(self) -> None:
        super().__init__(hv=self.get_obj().NODEs.hv, lv=self.get_obj().NODEs.lv)

    def decouple(self):
        return (
            super()
            .decouple()
            .builder(
                lambda c: c.PARAMs.rated_voltage.merge(
                    Range.lower_bound(float(self.get_obj().PARAMs.voltage) * 2.0)
                )
            )
        )


class can_be_surge_protected_power(can_be_surge_protected_defined):
    def __init__(self) -> None:
        super().__init__(
            low_potential=self.get_obj().NODEs.lv, *self.get_obj().NODEs.hv
        )

    def protect(self):
        return (
            super()
            .protect()
            .builder(
                lambda t: t.PARAMs.reverse_working_voltage.merge(
                    self.get_obj().PARAMs.voltage
                )
            )
        )


class ElectricPower(Power):
    def __init__(self) -> None:
        super().__init__()

        class NODES(Power.NODES()):
            hv = Electrical()
            lv = Electrical()

        self.NODEs = NODES(self)

        class PARAMS(Power.PARAMS()):
            voltage = TBD()

        self.PARAMs = PARAMS(self)

        # self.PARAMs.voltage.merge(
        #    self.NODEs.hv.PARAMs.potential - self.NODEs.lv.PARAMs.potential
        # )

        self.add_trait(can_be_surge_protected_power())
        self.add_trait(can_be_decoupled_power())

        from faebryk.library.has_single_electric_reference_defined import (
            has_single_electric_reference_defined,
        )

        self.add_trait(has_single_electric_reference_defined(self))

    def _on_connect(self, other: ModuleInterface) -> None:
        super()._on_connect(other)

        if not isinstance(other, ElectricPower):
            return

        self.PARAMs.voltage.merge(other.PARAMs.voltage)
