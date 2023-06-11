import logging

from faebryk.library.core import Component
from faebryk.library.library.interfaces import Electrical
from faebryk.library.trait_impl.component import (
    has_defined_type_description,
)

logger = logging.getLogger("BJT")


class BJT(Component):
    def __new__(cls):
        self = super().__new__(cls)
        self._setup_traits()
        return self

    def __init__(self) -> None:
        super().__init__()
        self._setup_interfaces()

    def _setup_traits(self):
        self.add_trait(has_defined_type_description("BJT"))

    def _setup_interfaces(self):
        class _IFs(Component.InterfacesCls()):
            emitter = Electrical()
            base = Electrical()
            collector = Electrical()

        self.IFs = _IFs(self)
