import logging

from faebryk.library.core import Component, Parameter
from faebryk.library.library.interfaces import Electrical
from faebryk.library.library.parameters import Constant
from faebryk.library.trait_impl.component import can_bridge_defined
from faebryk.library.traits.component import has_type_description
from faebryk.library.util import times, unit_map

logger = logging.getLogger("Resistor")


class Resistor(Component):
    def _setup_traits(self):
        # class _contructable_from_component(contructable_from_component.impl()):
        #    @staticmethod
        #    def from_component(comp: Component, resistance: Parameter) -> Resistor:
        #        interfaces = comp.IFs.get_all()
        #        assert len(interfaces) == 2
        #        assert len([i for i in interfaces if type(i) is not Electrical]) == 0

        #        r = Resistor.__new__(Resistor)
        #        r.set_resistance(resistance)
        #        class _IFs(Component.InterfacesCls()):
        #            unnamed = interfaces

        #        r.IFs = _IFs(r)

        #        return r

        # self.add_trait(_contructable_from_component())
        pass

    def _setup_interfaces(self):
        class _IFs(Component.InterfacesCls()):
            unnamed = times(2, Electrical)

        self.IFs = _IFs(self)

        self.add_trait(can_bridge_defined(*self.IFs.unnamed))

    def __new__(cls, *args, **kwargs):
        self = super().__new__(cls)
        self._setup_traits()
        return self

    def __init__(self, resistance: Parameter):
        super().__init__()

        self._setup_interfaces()
        self.set_resistance(resistance)

    def set_resistance(self, resistance: Parameter):
        self.resistance = resistance

        if type(resistance) is not Constant:
            # TODO this is a bit ugly
            # it might be that there was another more abstract valid trait
            # but this challenges the whole trait overriding mechanism
            # might have to make a trait stack thats popped or so
            self.del_trait(has_type_description)
            return

        class _has_type_description(has_type_description.impl()):
            @staticmethod
            def get_type_description():
                assert isinstance(self.resistance, Constant)
                resistance: Constant = self.resistance
                return unit_map(
                    resistance.value, ["µΩ", "mΩ", "Ω", "KΩ", "MΩ", "GΩ"], start="Ω"
                )

        self.add_trait(_has_type_description())
