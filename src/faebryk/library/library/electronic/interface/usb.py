import logging

from faebryk.library.core import Interface
from faebryk.library.library.electronic.interface.differential_pair import (
    DifferentialPair,
)
from faebryk.library.library.interfaces import Electrical

logger = logging.getLogger("USB")


class USB2_0(Interface):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)

        class _IFs(Interface.InterfacesCls()):
            usb = DifferentialPair()
            dp = usb.IFs.p
            dn = usb.IFs.n
            gnd = Electrical()

        self.IFs = _IFs(self)

    def connect(self, other: Interface) -> Interface:
        # TODO feels a bit weird
        # maybe we need to look at how aggregate interfaces connect
        assert type(other) is USB2_0, "can't connect to non USB2_0"
        for s, d in zip(self.IFs.get_all(), other.IFs.get_all()):
            s.connect(d)

        return self


class USB3_1(Interface):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._setup_interfaces()
        # self._setup_traits()
        self._setup_internal_connections()

    def _setup_interfaces(self):
        class _IFs(Interface.InterfacesCls()):
            usb = USB2_0()
            dp = usb.IFs.dp
            dn = usb.IFs.dn
            usb3_rx = DifferentialPair()
            std_ssrx_p = usb3_rx.IFs.p
            std_ssrx_n = usb3_rx.IFs.n
            usb3_tx = DifferentialPair()
            std_sstx_p = usb3_tx.IFs.p
            std_sstx_n = usb3_tx.IFs.n
            gnd_drain = Electrical()
            gnd = Electrical()

        self.IFs = _IFs(self)

    def _setup_internal_connections(self):
        self.IFs.gnd.connect_all(
            [
                self.IFs.usb.IFs.gnd,
                self.IFs.gnd_drain,
            ]
        )

    def connect(self, other: Interface) -> Interface:
        # TODO feels a bit weird
        # maybe we need to look at how aggregate interfaces connect
        assert type(other) is USB3_1, "can't connect to non USB3_1"
        for s, d in zip(self.IFs.get_all(), other.IFs.get_all()):
            s.connect(d)

        return self
