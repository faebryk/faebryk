# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

from faebryk.core.core import Module, NodeTrait, Parameter
from faebryk.core.util import unit_map
from faebryk.library.Constant import Constant
from faebryk.library.Electrical import Electrical
from faebryk.library.TBD import TBD
from faebryk.library.can_bridge_defined import can_bridge_defined
from faebryk.library.has_type_description import has_type_description
from faebryk.libs.util import times


class Diode(Module):
    def __new__(cls, *args, **kwargs):
        self = super().__new__(cls)
        self._setup_traits()
        return self

    def __init__(self, forward_voltage: Parameter):
        super().__init__()
        self._setup_interfaces()
        self.set_forward_voltage(forward_voltage)

    def _setup_traits(self):
        class _has_type_description(has_type_description.impl()):
            @staticmethod
            def get_type_description():
                assert isinstance(self.forward_voltage, Constant)
                return unit_map(
                    self.forward_voltage.value,
                    ["µV", "mV", "V", "KV", "MV", "GV"],
                    start="F",
                )

            def is_implemented(self):
                c = self.get_obj()
                assert isinstance(c, Diode)
                return type(c.forward_voltage) is Constant

        self.add_trait(_has_type_description())

    def _setup_interfaces(self):
        class _IFs(super().IFS()):
            annode = Electrical()
            cathode = Electrical()

        self.IFs = _IFs(self)
        self.add_trait(can_bridge_defined(self.IFs.annode, self.IFs.cathode))

    def set_forward_voltage(self, forward_voltage: Parameter):
        self.forward_voltage = forward_voltage

        if type(forward_voltage) is not Constant:
            return
        _forward_voltage: Constant = forward_voltage

        class _has_type_description(has_type_description.impl()):
            @staticmethod
            def get_type_description():
                return unit_map(
                    _forward_voltage.value,
                    ["µV", "mV", "V", "kV", "MV", "GV"],
                    start="V",
                )

        self.add_trait(_has_type_description())
