# This file is part of the faebryk project
# SPDX-License-Identifier: MIT


from enum import Enum, auto

from faebryk.core.core import Parameter
from faebryk.library.Constant import Constant
from faebryk.library.Diode import Diode
from faebryk.library.Electrical import Electrical
from faebryk.library.ElectricPower import ElectricPower
from faebryk.library.Resistor import Resistor
from faebryk.library.TBD import TBD


class LED(Diode):
    class Color(Enum):
        RED = auto()
        GREEN = auto()
        BLUE = auto()
        YELLOW = auto()
        WHITE = auto()

    class HumanBrightness(Enum):
        """
        Human brightness perception in mcd (millicandela) for different light sources.
        """

        GLOW_OF_STAR = Constant(0.001)  # Glow of a star on a clear night
        DISTANT_STREETLIGHT = Constant(
            0.01
        )  # Distant streetlight seen from a few kilometers away
        FULL_MOON = Constant(1)  # Typical full moon
        CANDLES = Constant(10)  # Candles in a dark room
        DIMMED_LED = Constant(50)  # Dimmed LED night light
        STANDBY_LED = Constant(100)  # LED on electronic devices (standby indicator)
        INDOOR_LIGHTING = Constant(500)  # Standard indoor lighting (incandescent bulb)
        COMPUTER_SCREEN = Constant(1000)  # Computer screen at average brightness
        OUTDOOR_LIGHTING = Constant(5000)  # Typical outdoor lighting (streetlight)
        BRIGHT_LED_FLASHLIGHT = Constant(10000)  # Bright LED flashlight
        CAR_HEADLIGHT_LOW = Constant(20000)  # Car headlight (low beam)
        CAR_HEADLIGHT_HIGH = Constant(50000)  # Car headlight (high beam)
        DIRECT_SUNLIGHT = Constant(100000)  # Direct sunlight

        def __repr__(self):
            return f"{self.name}: {self.value} mcd"

    @classmethod
    def PARAMS(cls):
        class _PARAMs(super().PARAMS()):
            brightness = TBD[float]()
            max_brightness = TBD[float]()
            color = TBD[cls.Color]()

        return _PARAMs

    def __init__(self) -> None:
        super().__init__()

        self.PARAMs = self.PARAMS()(self)

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

    def connect_via_current_limiting_resistor_to_power(
        self, resistor: Resistor, power: ElectricPower, low_side: bool
    ):
        self.connect_via_current_limiting_resistor(
            power.PARAMs.voltage,
            resistor,
            power.IFs.lv if low_side else power.IFs.hv,
            low_side,
        )
