import logging

from faebryk.library.core import Component, Parameter
from faebryk.library.library.interfaces import Electrical
from faebryk.library.library.parameters import Constant
from faebryk.library.trait_impl.component import can_bridge_defined
from faebryk.library.traits.component import has_type_description
from faebryk.library.util import times, unit_map

logger = logging.getLogger(__name__)


class Capacitor(Component):
    def __new__(cls, *args, **kwargs):
        self = super().__new__(cls)
        self._setup_traits()
        return self

    def __init__(self, capacitance: Parameter):
        super().__init__()

        self._setup_interfaces()
        self.set_capacitance(capacitance)

    def _setup_traits(self):
        pass

    def _setup_interfaces(self):
        class _IFs(Component.InterfacesCls()):
            unnamed = times(2, Electrical)

        self.IFs = _IFs(self)
        self.add_trait(can_bridge_defined(*self.IFs.unnamed))

    def set_capacitance(self, capacitance: Parameter):
        self.capacitance = capacitance

        if type(capacitance) is not Constant:
            return
        _capacitance: Constant = capacitance

        class _has_type_description(has_type_description.impl()):
            @staticmethod
            def get_type_description():
                return unit_map(
                    _capacitance.value, ["µF", "mF", "F", "KF", "MF", "GF"], start="F"
                )

        self.add_trait(_has_type_description())
