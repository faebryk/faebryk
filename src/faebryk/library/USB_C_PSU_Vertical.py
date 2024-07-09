from faebryk.core.core import Module
from faebryk.core.util import connect_all_interfaces
from faebryk.library.can_be_decoupled import can_be_decoupled
from faebryk.library.can_bridge_defined import can_bridge_defined
from faebryk.library.Capacitor import Capacitor
from faebryk.library.Constant import Constant
from faebryk.library.ElectricPower import ElectricPower
from faebryk.library.Fuse import Fuse
from faebryk.library.Resistor import Resistor
from faebryk.library.USB2_0 import USB2_0
from faebryk.libs.units import M, k, n
from faebryk.libs.util import times
from vindriktning_esp32_c3.library.USB_Type_C_Receptacle_14_pin_Vertical import (
    USB_Type_C_Receptacle_14_pin_Vertical,
)
from vindriktning_esp32_c3.library.USBLC6_2P6 import USBLC6_2P6


class USB_C_PSU_Vertical(Module):
    class USB_2_0_ESD(Module):
        """
        USB 2.0 ESD protection
        """

        def __init__(self) -> None:
            super().__init__()

            class _IFs(Module.IFS()):
                usb_in = USB2_0()
                usb_out = USB2_0()

            self.IFs = _IFs(self)

            class _NODEs(Module.NODES()):
                esd = USBLC6_2P6()

            self.NODEs = _NODEs(self)

            # connect
            self.IFs.usb_in.connect_via(self.NODEs.esd, self.IFs.usb_out)

            # Add bridge trait
            self.add_trait(can_bridge_defined(self.IFs.usb_in, self.IFs.usb_out))

    def __init__(self) -> None:
        super().__init__()

        # interfaces
        class _IFs(Module.IFS()):
            power_out = ElectricPower()
            usb = USB2_0()

        self.IFs = _IFs(self)

        # components
        class _NODEs(Module.NODES()):
            usb_connector = USB_Type_C_Receptacle_14_pin_Vertical()
            configuration_resistors = times(2, Resistor)
            gnd_resistor = Resistor()
            gnd_capacitor = Capacitor()
            esd = USBLC6_2P6()
            fuse = Fuse()

        self.NODEs = _NODEs(self)

        self.NODEs.gnd_capacitor.PARAMs.capacitance.merge(100 * n)
        self.NODEs.gnd_capacitor.PARAMs.rated_voltage.merge(1000)
        self.NODEs.gnd_resistor.PARAMs.resistance.merge(1 * M)
        for res in self.NODEs.configuration_resistors:
            res.PARAMs.resistance.merge(5.1 * k)
        self.NODEs.fuse.PARAMs.fuse_type.merge(Fuse.FuseType.RESETTABLE)
        self.NODEs.fuse.PARAMs.trip_current.merge(Constant(1))

        # alliases
        vcon = self.NODEs.usb_connector.IFs.vbus
        vusb = self.IFs.usb.IFs.buspower
        gnd = vusb.IFs.lv

        vcon.connect_via(self.NODEs.fuse, vusb)
        vusb.connect(self.NODEs.esd.IFs.usb.IFs.buspower)
        vusb.IFs.lv.connect(gnd)
        connect_all_interfaces(
            [self.NODEs.usb_connector.IFs.usb, self.IFs.usb, self.NODEs.esd.IFs.usb]
        )

        # configure as ufp with 5V@max3A
        self.NODEs.usb_connector.IFs.cc1.connect_via(
            self.NODEs.configuration_resistors[0], gnd
        )
        self.NODEs.usb_connector.IFs.cc2.connect_via(
            self.NODEs.configuration_resistors[1], gnd
        )

        self.NODEs.esd.IFs.usb.IFs.buspower.get_trait(
            can_be_decoupled
        ).decouple()  # TODO: 1 uf

        # EMI shielding
        self.NODEs.usb_connector.IFs.shield.connect_via(self.NODEs.gnd_resistor, gnd)
        self.NODEs.usb_connector.IFs.shield.connect_via(self.NODEs.gnd_capacitor, gnd)
