import logging

from faebryk.library.core import Component, ComponentTrait, Parameter
from faebryk.library.library.interfaces import Electrical
from faebryk.library.library.parameters import Constant
from faebryk.library.trait_impl.component import (
    has_defined_type_description,
)

logger = logging.getLogger(__name__)


class LED(Component):
    class has_calculatable_needed_series_resistance(ComponentTrait):
        @staticmethod
        def get_needed_series_resistance_ohm(input_voltage_V: float) -> Constant:
            raise NotImplementedError

    def _setup_traits(self):
        self.add_trait(has_defined_type_description("LED"))

    def _setup_interfaces(self):
        class _IFs(Component.InterfacesCls()):
            anode = Electrical()
            cathode = Electrical()

        self.IFs = _IFs(self)

    def __new__(cls):
        self = super().__new__(cls)
        self._setup_traits()
        return self

    def __init__(self) -> None:
        super().__init__()
        self._setup_interfaces()

    def set_forward_parameters(self, voltage_V: Parameter, current_A: Parameter):
        if type(voltage_V) is Constant and type(current_A) is Constant:
            _voltage_V: Constant = voltage_V
            _current_A: Constant = current_A

            class _(self.has_calculatable_needed_series_resistance.impl()):
                @staticmethod
                def get_needed_series_resistance_ohm(
                    input_voltage_V: float,
                ) -> Constant:
                    return LED.needed_series_resistance_ohm(
                        input_voltage_V, _voltage_V.value, _current_A.value
                    )

            self.add_trait(_())

    @staticmethod
    def needed_series_resistance_ohm(
        input_voltage_V: float, forward_voltage_V: float, forward_current_A: float
    ) -> Constant:
        return Constant(int((input_voltage_V - forward_voltage_V) / forward_current_A))
