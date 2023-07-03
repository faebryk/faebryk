import logging

from faebryk.library.core import Interface
from faebryk.library.library.interfaces import Electrical

logger = logging.getLogger(__name__)


class UART_SIMPLE(Interface):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)

        class _IFs(Interface.InterfacesCls()):
            rx = Electrical()
            tx = Electrical()
            gnd = Electrical()

        self.IFs = _IFs(self)

    def connect(self, other: Interface) -> Interface:
        # TODO feels a bit weird
        # maybe we need to look at how aggregate interfaces connect
        assert type(other) is UART_SIMPLE or UART, "can't connect to non UART"
        if type(other) is UART:
            self.IFs.rx.connect(other.IFs.rx)
            self.IFs.tx.connect(other.IFs.tx)
            self.IFs.gnd.connect(other.IFs.gnd)
        else:
            for s, d in zip(self.IFs.get_all(), other.IFs.get_all()):
                s.connect(d)

        return self


class UART(Interface):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)

        class _IFs(Interface.InterfacesCls()):
            rx = Electrical()
            tx = Electrical()
            rts = Electrical()
            cts = Electrical()
            dtr = Electrical()
            dsr = Electrical()
            gnd = Electrical()

        self.IFs = _IFs(self)

    def connect(self, other: Interface) -> Interface:
        # TODO feels a bit weird
        # maybe we need to look at how aggregate interfaces connect
        assert type(other) is UART or UART_SIMPLE, "can't connect to non UART"
        if type(other) is UART_SIMPLE:
            self.IFs.rx.connect(other.IFs.rx)
            self.IFs.tx.connect(other.IFs.tx)
            self.IFs.gnd.connect(other.IFs.gnd)
        else:
            for s, d in zip(self.IFs.get_all(), other.IFs.get_all()):
                s.connect(d)

        return self
