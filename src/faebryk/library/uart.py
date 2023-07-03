from faebryk.library.Electrical import Electrical
from faebryk.library.UART_Base import UART_Base


class UART(UART_Base):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)

        class _NODEs(super().NODES):
            rts = Electrical()
            cts = Electrical()
            dtr = Electrical()
            dsr = Electrical()

        self.NODEs = _NODEs(self)
