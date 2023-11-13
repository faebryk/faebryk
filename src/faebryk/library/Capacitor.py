# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

from faebryk.core.core import Module, Parameter
from faebryk.core.util import unit_map
from faebryk.library.can_bridge_defined import can_bridge_defined
from faebryk.library.Constant import Constant
from faebryk.library.Electrical import Electrical
from faebryk.library.has_type_description import has_type_description
from faebryk.libs.util import times
from faebryk.library.has_defined_capacitance import has_defined_capacitance
from faebryk.library.has_capacitance import has_capacitance


class Capacitor(Module):
    def __new__(cls, *args, **kwargs):
        self = super().__new__(cls)
        self._setup_traits()
        return self

    def __init__(self, capacitance: Parameter):
        super().__init__()
        self._setup_interfaces()
        self.set_capacitance(capacitance)

    def _setup_traits(self):
        class _has_type_description(has_type_description.impl()):
            @staticmethod
            def get_type_description():
                assert isinstance(
                    self.get_trait(has_capacitance).get_capacitance(), Constant
                )
                capacitance = self.get_trait(has_capacitance).get_capacitance()
                return unit_map(
                    self.capacitance.value,
                    ["µF", "mF", "F", "KF", "MF", "GF"],
                    start="F",
                )

            def is_implemented(self):
                c = self.get_obj()
                assert isinstance(c, Capacitor)
                return type(c.capacitance) is Constant

        self.add_trait(_has_type_description())

    def _setup_interfaces(self):
        class _IFs(super().IFS()):
            unnamed = times(2, Electrical)

        self.IFs = _IFs(self)
        self.add_trait(can_bridge_defined(*self.IFs.unnamed))

    def set_capacitance(self, capacitance: Parameter):
        self.add_trait(has_defined_capacitance(capacitance))
        if type(capacitance) is not Constant:
            # TODO this is a bit ugly
            # it might be that there was another more abstract valid trait
            # but this challenges the whole trait overriding mechanism
            # might have to make a trait stack thats popped or so
            self.del_trait(has_type_description)
            return

        class _has_type_description(has_type_description.impl()):
            @staticmethod
            def get_type_description():
                return unit_map(
                    _capacitance.value, ["µF", "mF", "F", "kF", "MF", "GF"], start="F"
                )

        self.add_trait(_has_type_description())
