import logging

from faebryk.library.core import Interface
from faebryk.library.library.interfaces import Electrical

logger = logging.getLogger("Differential pair")


class DifferentialPair(Interface):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)

        class _IFs(Interface.InterfacesCls()):
            p = Electrical()
            n = Electrical()

        self.IFs = _IFs(self)

    def connect(self, other: Interface) -> Interface:
        assert type(other) is DifferentialPair, "can't connect to different type"
        for s, d in zip(self.IFs.get_all(), other.IFs.get_all()):
            s.connect(d)

        return self
