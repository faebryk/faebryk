from enum import Enum
import logging

from faebryk.library.core import Component
from faebryk.library.library.interfaces import Electrical
from faebryk.library.library.parameters import Constant, Range
from faebryk.library.trait_impl.component import (
    has_defined_type_description,
)

logger = logging.getLogger("DIODE")


class DIODE(Component):
    class JunctionType(Enum):
        PN = 1
        SCHOTTKEY = 2

    class OperatingRegion(Enum):
        BREAKDOWN = 1
        REVERSE_BIASED = 2
        FORWARD_BIASED = 3
        LEVELING_OFF = 4

    def _setup_traits(self):
        self.add_trait(has_defined_type_description("DIODE"))

    def _setup_interfaces(self):
        class _IFs(Component.InterfacesCls()):
            anode = Electrical()
            cathode = Electrical()

        self.IFs = _IFs(self)

    def __new__(cls):
        self = super().__new__(cls)
        self._setup_traits()
        return self

    def __init__(
        self,
        junction_operating_temperature: Range,
        maximum_average_forward_rectified_current: Constant,
        forward_threshold_voltage: Constant,
        maximum_dc_blocking_voltage: Constant,
        maximum_full_load_reverse_current: Constant,
        maximum_repetitive_peak_reverse_voltage: Constant,
        junction_type: JunctionType,
    ) -> None:
        super().__init__()

        self.junction_operating_temperature = junction_operating_temperature
        self.maximum_average_forward_rectified_current = (
            maximum_average_forward_rectified_current
        )
        self.forward_threshold_voltage = forward_threshold_voltage
        self.maximum_dc_blocking_voltage = maximum_dc_blocking_voltage
        self.maximum_full_load_reverse_current = maximum_full_load_reverse_current
        self.maximum_repetitive_peak_reverse_voltage = (
            maximum_repetitive_peak_reverse_voltage
        )
        self.junction_type = junction_type

        self._setup_interfaces()
