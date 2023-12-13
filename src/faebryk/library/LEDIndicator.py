# This file is part of the faebryk project
# SPDX-License-Identifier: MIT
from faebryk.core.core import Module
from faebryk.library.ElectricLogic import ElectricLogic
from faebryk.library.ElectricPower import ElectricPower
from faebryk.library.PoweredLED import PoweredLED
from faebryk.library.PowerSwitch import can_switch_power_defined


class LEDIndicator(Module):
    class Switch(Module):
        def __init__(self) -> None:
            super().__init__()

            class _IFs(Module.IFS()):
                power_in = ElectricPower()
                power_out = ElectricPower()
                logic_in = ElectricLogic()

            self.IFs = _IFs(self)

            self.add_trait(
                can_switch_power_defined(
                    self.IFs.power_in, self.IFs.power_out, self.IFs.logic_in
                )
            )

    # Just bridges power through statically
    # useful when using a switched power input as logic signal
    class StaticSwitch(Switch):
        def __init__(self) -> None:
            super().__init__()

            self.IFs.power_in.connect(self.IFs.power_out)
            self.IFs.logic_in.connect_reference(self.IFs.power_in)
            self.IFs.logic_in.set(True)

    def __init__(self) -> None:
        super().__init__()

        # interfaces
        class _IFs(Module.IFS()):
            logic_in = ElectricLogic()
            power_in = ElectricPower()

        self.IFs = _IFs(self)

        # components
        class _NODEs(Module.NODES()):
            led = PoweredLED()
            power_switch = LEDIndicator.Switch()

        self.NODEs = _NODEs(self)

        #
        self.IFs.power_in.connect_via(self.NODEs.power_switch, self.NODEs.led.IFs.power)
        self.NODEs.power_switch.IFs.logic_in.connect(self.IFs.logic_in)
