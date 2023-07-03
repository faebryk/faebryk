from faebryk.core.core import ModuleInterface
from faebryk.library.Electrical import Electrical
from faebryk.libs.util import times


class MultiSPI(ModuleInterface):
    def __init__(self, data_lane_count: int) -> None:
        super().__init__()

        class _NODEs(ModuleInterface.NODES()):
            data = times(data_lane_count, Electrical)
            sclk = Electrical()
            ss_n = Electrical()
            gnd = Electrical()

        self.NODEs = _NODEs(self)
