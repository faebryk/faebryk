from enum import Enum
import logging

from faebryk.library.core import Component
from faebryk.library.library.interfaces import Electrical
from faebryk.library.trait_impl.component import (
    can_bridge_defined,
    has_defined_type_description,
)

logger = logging.getLogger(__name__)


class BJT(Component):
    class DopingType(Enum):
        NPN = 1
        PNP = 2

    # TODO use this, here is more info: https://en.wikipedia.org/wiki/Bipolar_junction_transistor#Regions_of_operation
    class OperationRegion(Enum):
        ACTIVE = 1
        INVERTED = 2
        SATURATION = 3
        CUT_OFF = 4

    def __new__(cls):
        self = super().__new__(cls)
        self._setup_traits()
        return self

    def __init__(
        self, doping_type: DopingType, operation_region: OperationRegion
    ) -> None:
        super().__init__()

        self.doping_type = doping_type
        self.operation_region = operation_region

        self._setup_interfaces()

    def _setup_traits(self):
        self.add_trait(has_defined_type_description("BJT"))

    def _setup_interfaces(self):
        class _IFs(Component.InterfacesCls()):
            emitter = Electrical()
            base = Electrical()
            collector = Electrical()

        self.IFs = _IFs(self)
        # TODO pretty confusing
        self.add_trait(
            can_bridge_defined(in_if=self.IFs.collector, out_if=self.IFs.emitter)
        )
