import logging

from faebryk.library.core import Component
from faebryk.library.library.interfaces import Electrical
from faebryk.library.trait_impl.component import (
    can_bridge_defined,
    has_defined_type_description,
)
from faebryk.library.util import times

logger = logging.getLogger("Switch")


class Switch(Component):
    def _setup_traits(self):
        self.add_trait(has_defined_type_description("SW"))

    def _setup_interfaces(self):
        class _IFs(Component.InterfacesCls()):
            unnamed = times(2, Electrical)

        self.IFs = _IFs(self)
        self.add_trait(can_bridge_defined(*self.IFs.unnamed))

    def __new__(cls):
        self = super().__new__(cls)
        self._setup_traits()
        return self

    def __init__(self) -> None:
        super().__init__()
        self._setup_interfaces()
