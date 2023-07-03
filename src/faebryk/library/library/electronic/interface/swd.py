import logging

from faebryk.library.core import Interface
from faebryk.library.library.interfaces import Electrical

logger = logging.getLogger(__name__)


class SWD(Interface):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)

        class _IFs(Interface.InterfacesCls()):
            clk = Electrical()
            dio = Electrical()
            gnd = Electrical()

        self.IFs = _IFs(self)

    def connect(self, other: Interface) -> Interface:
        # TODO feels a bit weird
        # maybe we need to look at how aggregate interfaces connect
        assert type(other) is SWD, "can't connect to non SWD"
        for s, d in zip(self.IFs.get_all(), other.IFs.get_all()):
            s.connect(d)

        return self
