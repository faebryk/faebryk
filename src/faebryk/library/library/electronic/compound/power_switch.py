import logging

from faebryk.library.core import Component
from faebryk.library.library.electronic.base.mosfet import MOSFET
from faebryk.library.library.electronic.base.resisistor import Resistor
from faebryk.library.library.interfaces import Electrical, Power
from faebryk.library.library.parameters import TBD
from faebryk.library.trait_impl.component import can_bridge_defined

logger = logging.getLogger("Power switch")


class PowerSwitch(Component):
    def __init__(self, lowside: bool, normally_closed: bool) -> None:
        super().__init__()  # interfaces

        self.lowside = lowside
        self.normally_closed = normally_closed

        class _IFs(Component.InterfacesCls()):
            # TODO replace with logical
            logic_in = Electrical()
            power_in = Power()
            switched_power_out = Power()

        self.IFs = _IFs(self)

        # components
        class _CMPs(Component.ComponentsCls()):
            mosfet = MOSFET(
                MOSFET.ChannelType.N_CHANNEL
                if lowside
                else MOSFET.ChannelType.P_CHANNEL,
                MOSFET.SaturationType.ENHANCEMENT,
            )
            pull_resistor = Resistor(TBD())

        self.CMPs = _CMPs(self)

        # pull gate
        self.CMPs.mosfet.IFs.gate.connect_via(
            self.CMPs.pull_resistor,
            self.IFs.power_in.IFs.lv
            if lowside and not normally_closed
            else self.IFs.power_in.IFs.hv,
        )

        # connect gate to logic
        self.IFs.logic_in.connect(self.CMPs.mosfet.IFs.gate)

        # passthrough non-switched side, bridge switched side
        if lowside:
            self.IFs.power_in.IFs.hv.connect(self.IFs.switched_power_out.IFs.hv)
            self.IFs.power_in.IFs.lv.connect_via(
                self.CMPs.mosfet, self.IFs.switched_power_out.IFs.lv
            )
        else:
            self.IFs.power_in.IFs.lv.connect(self.IFs.switched_power_out.IFs.lv)
            self.IFs.power_in.IFs.hv.connect_via(
                self.CMPs.mosfet, self.IFs.switched_power_out.IFs.hv
            )

        # TODO pretty confusing
        # Add bridge trait
        self.add_trait(
            can_bridge_defined(self.IFs.power_in, self.IFs.switched_power_out)
        )
