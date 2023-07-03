from faebryk.core.core import ModuleInterface
from faebryk.library.Electrical import Electrical


class UART_Base(ModuleInterface):
    class NODES(ModuleInterface.NODES()):
        rx = Electrical()
        tx = Electrical()
        gnd = Electrical()

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)

        self.NODEs = UART_Base.NODES(self)
