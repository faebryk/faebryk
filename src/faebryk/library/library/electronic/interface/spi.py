import logging

from faebryk.library.core import Interface
from faebryk.library.library.interfaces import Electrical

logger = logging.getLogger(__name__)


class SPI(Interface):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)

        class _IFs(Interface.InterfacesCls()):
            sclk = Electrical()
            miso = Electrical()
            mosi = Electrical()
            gnd = Electrical()

        self.IFs = _IFs(self)

    def connect(self, other: Interface) -> Interface:
        # TODO feels a bit weird
        # maybe we need to look at how aggregate interfaces connect
        assert type(other) is SPI, "can't connect to non SPI"
        for s, d in zip(self.IFs.get_all(), other.IFs.get_all()):
            s.connect(d)

        return self


class QUAD_SPI(Interface):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)

        class _IFs(Interface.InterfacesCls()):
            sd0 = Electrical()
            sd1 = Electrical()
            sd2 = Electrical()
            sd3 = Electrical()
            sclk = Electrical()
            ss_n = Electrical()
            gnd = Electrical()

        self.IFs = _IFs(self)

    def connect(self, other: Interface) -> Interface:
        # TODO feels a bit weird
        # maybe we need to look at how aggregate interfaces connect
        assert type(other) is QUAD_SPI, "can't connect to non QUAD_SPI"
        for s, d in zip(self.IFs.get_all(), other.IFs.get_all()):
            s.connect(d)

        return self
