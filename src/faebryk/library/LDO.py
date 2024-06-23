# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

from enum import IntEnum, auto

from faebryk.core.core import Module
from faebryk.core.util import as_unit, as_unit_with_tolerance
from faebryk.library.ElectricPower import ElectricPower
from faebryk.library.has_designator_prefix_defined import has_designator_prefix_defined
from faebryk.library.has_pin_association_heuristic_lookup_table import (
    has_pin_association_heuristic_lookup_table,
)
from faebryk.library.has_simple_value_representation_based_on_params import (
    has_simple_value_representation_based_on_params,
)
from faebryk.library.TBD import TBD


class LDO(Module):
    class OutputType(IntEnum):
        FIXED = auto()
        ADJUSTABLE = auto()

    class OutputPolarity(IntEnum):
        POSITIVE = auto()
        NEGATIVE = auto()

    @classmethod
    def PARAMS(cls):
        class _PARAMs(super().PARAMS()):
            max_input_voltage = TBD[float]()
            output_voltage = TBD[float]()
            output_polarity = TBD[LDO.OutputPolarity]()
            output_type = TBD[LDO.OutputType]()
            output_current = TBD[float]()
            psrr = TBD[float]()
            dropout_voltage = TBD[float]()
            number_of_outputs = TBD[int]()

        return _PARAMs

    def __init__(self):
        super().__init__()

        self.PARAMs = self.PARAMS()(self)

        class _IFs(super().IFS()):
            v_in = ElectricPower()
            v_out = ElectricPower()

        self.IFs = _IFs(self)

        self.add_trait(
            has_simple_value_representation_based_on_params(
                (
                    self.PARAMs.output_polarity,
                    self.PARAMs.output_type,
                    self.PARAMs.output_voltage,
                    self.PARAMs.output_current,
                    self.PARAMs.psrr,
                    self.PARAMs.dropout_voltage,
                    self.PARAMs.number_of_outputs,
                    self.PARAMs.max_input_voltage,
                ),
                lambda ps: "LDO "
                + " ".join(
                    [
                        as_unit_with_tolerance(ps[2], "V"),
                        as_unit(ps[3], "A"),
                        as_unit(ps[4], "dB"),
                        as_unit(ps[5], "V"),
                        f"{ps[6]} outputs",
                        f"Vin max {as_unit(ps[7], 'V')}",
                    ]
                ),
            )
        )
        self.add_trait(has_designator_prefix_defined("U"))
        self.add_trait(
            has_pin_association_heuristic_lookup_table(
                mapping={
                    self.IFs.v_in.IFs.hv: ["Vin", "Vi"],
                    self.IFs.v_out.IFs.hv: ["Vout", "Vo"],
                    self.IFs.v_in.IFs.lv: ["GND", "V-"],
                },
                accept_prefix=False,
                case_sensitive=False,
            )
        )
