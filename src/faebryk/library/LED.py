# This file is part of the faebryk project
# SPDX-License-Identifier: MIT


from faebryk.core.core import Parameter
from faebryk.library.Diode import Diode
from faebryk.library.Electrical import Electrical
from faebryk.library.Resistor import Resistor
from faebryk.library.TBD import TBD


class LED(Diode):
    def __init__(self) -> None:
        super().__init__()

        class _PARAMs(type(super().PARAMS())):
            brightness = TBD[float]()
            max_brightness = TBD[float]()

        self.PARAMs = _PARAMs(self)

        self.PARAMs.current.merge(
            self.PARAMs.brightness
            / self.PARAMs.max_brightness
            * self.PARAMs.max_current
        )

    def set_intensity(self, intensity: Parameter[float]) -> None:
        self.PARAMs.brightness.merge(intensity * self.PARAMs.max_brightness)

    def connect_via_current_limiting_resistor(
        self,
        input_voltage: Parameter[float],
        resistor: Resistor,
        target: Electrical,
        low_side: bool,
    ):
        if low_side:
            self.IFs.cathode.connect_via(resistor, target)
        else:
            self.IFs.anode.connect_via(resistor, target)

        resistor.PARAMs.resistance.merge(
            self.get_needed_series_resistance_for_current_limit(input_voltage),
        )
