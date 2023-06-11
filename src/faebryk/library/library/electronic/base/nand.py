import logging

from faebryk.library.core import Component
from faebryk.library.library.interfaces import Electrical, Power
from faebryk.library.traits.component import contructable_from_component
from faebryk.library.traits.interface import contructable_from_interface_list
from faebryk.library.util import times
from faebryk.libs.util import consume_iterator

logger = logging.getLogger("NAND")


class NAND(Component):
    def _setup_traits(self):
        class _constructable_from_component(contructable_from_component.impl()):
            @staticmethod
            def from_comp(comp: Component) -> NAND:
                n = NAND.__new__(NAND)
                n.__init_from_comp(comp)
                return n

        self.add_trait(_constructable_from_component())

    def _setup_interfaces(self, input_cnt):
        class _IFs(Component.InterfacesCls()):
            power = Power()
            output = Electrical()
            inputs = times(input_cnt, Electrical)

        self.IFs = _IFs(self)

    def __new__(cls, *args, **kwargs):
        self = super().__new__(cls)

        self._setup_traits()

        return self

    def __init__(self, input_cnt: int):
        super().__init__()

        self._setup_interfaces(input_cnt)

    def __init_from_comp(self, comp: Component):
        interfaces = comp.IFs.get_all()
        assert all(map(lambda i: type(i) is Electrical, interfaces))

        it = iter(interfaces)

        self.IFs.power = (
            Power().get_trait(contructable_from_interface_list).from_interfaces(it)
        )
        self.IFs.output = (
            Electrical().get_trait(contructable_from_interface_list).from_interfaces(it)
        )
        self.IFs.inputs = list(
            consume_iterator(
                Electrical()
                .get_trait(contructable_from_interface_list)
                .from_interfaces,
                it,
            )
        )
