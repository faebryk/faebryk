# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

"""
This file contains a faebryk sample.
Faebryk samples demonstrate the usage by building example systems.
This particular sample creates a netlist with some resistors and a nand ic
    with no specific further purpose or function.
Thus this is a netlist sample.
Netlist samples can be run directly.
The netlist is printed to stdout.
"""

from abc import abstractmethod
from dataclasses import dataclass
from typing import Iterable

def run_experiment():
    # function imports
    from faebryk.exporters.netlist.kicad.netlist_kicad import from_faebryk_t2_netlist
    from faebryk.exporters.netlist import make_t2_netlist_from_t1
    from faebryk.exporters.netlist.graph import make_graph_from_components, make_t1_netlist_from_graph
    # library imports
    from faebryk.library.library.components import Resistor, LED
    from faebryk.library.library.parameters import Constant, TBD
    from faebryk.library.core import Interface, Component, InterfaceTrait
    from faebryk.library.library.interfaces import Electrical, Power
    from faebryk.library.traits.interface import can_list_interfaces, contructable_from_interface_list
    from faebryk.library.traits.component import has_defined_type_description, has_footprint_pinmap, has_defined_footprint, has_defined_footprint_pinmap, has_symmetric_footprint_pinmap
    from faebryk.library.library.footprints import SMDTwoPin

    class I2C(Interface):
        def __init__(self, component) -> None:
            super().__init__()
            self.set_component(component)

            self.SDA = Electrical()
            self.SCL = Electrical()
            self.GND = Electrical()


            class _can_list_interfaces(can_list_interfaces):
                @staticmethod
                def get_interfaces() -> list[Electrical]:
                    return [self.SDA, self.SCL, self.GND]

            self.add_trait(_can_list_interfaces())

        def connect(self, other: Interface):
            #TODO feels a bit weird
            # maybe we need to look at how aggregate interfaces connect
            assert(type(other) is I2C), "can't connect to other types"
            for s,d in zip(
                    self.get_trait(can_list_interfaces).get_interfaces(),
                    other.get_trait(can_list_interfaces).get_interfaces(),
                ):
                s.connect(d)

    class SDIO(Interface):
        def __init__(self, component) -> None:
            super().__init__()
            self.set_component(component)

            self.DATA = [Electrical() for _ in range(4)]
            self.CLK = Electrical()
            self.CMD = Electrical()
            self.GND = Electrical()

            class _can_list_interfaces(can_list_interfaces):
                @staticmethod
                def get_interfaces() -> list[Electrical]:
                    return [*self.DATA, self.CLK, self.CMD, self.GND]

            class _contructable_from_interface_list(contructable_from_interface_list):
                @staticmethod
                def from_interfaces(interfaces: Iterable[Electrical]) -> Electrical:
                    i = Electrical()
                    i.DATA = [next(interfaces) for _ in range(4)]
                    i.CLK = next(interfaces)
                    i.CMD = next(interfaces)
                    i.GND = next(interfaces)
                    return i

            self.add_trait(_can_list_interfaces())
            self.add_trait(_contructable_from_interface_list())

    class UART(Interface):
        def __init__(self, component) -> None:
            super().__init__()
            self.set_component(component)

            self.tx  = Electrical()
            self.rx  = Electrical()
            self.GND = Electrical()

            class _can_list_interfaces(can_list_interfaces):
                @staticmethod
                def get_interfaces() -> list[Electrical]:
                    return [self]

            class _contructable_from_interface_list(contructable_from_interface_list):
                @staticmethod
                def from_interfaces(interfaces: Iterable[Electrical]) -> Electrical:
                    i = Electrical()
                    i.tx = next(interfaces)
                    i.rx = next(interfaces)
                    i.GND = next(interfaces)
                    return i

            self.add_trait(_can_list_interfaces())
            self.add_trait(_contructable_from_interface_list())

    class JTAG(Interface):
        def __init__(self, component) -> None:
            super().__init__()
            self.set_component(component)

            self.MTDI = Electrical()
            self.MTCK = Electrical()
            self.MTMS = Electrical()
            self.MTDO = Electrical()
            self.GND = Electrical()

            class _can_list_interfaces(can_list_interfaces):
                @staticmethod
                def get_interfaces() -> list[Electrical]:
                    return [self]

            class _contructable_from_interface_list(contructable_from_interface_list):
                @staticmethod
                def from_interfaces(interfaces: Iterable[Electrical]) -> Electrical():
                    i = Electrical()
                    i.MTDI = next(interfaces)
                    i.MTCK = next(interfaces)
                    i.MTMS = next(interfaces)
                    i.MTDO = next(interfaces)
                    i.GND  = next(interfaces)
                    return i

            self.add_trait(_can_list_interfaces())
            self.add_trait(_contructable_from_interface_list())

    class ADC(Interface):
        def __init__(self, channel_count, component) -> None:
            super().__init__()
            self.set_component(component)

            self.CHANNELS = [Electrical() for _ in range(channel_count)]

            class _can_list_interfaces(can_list_interfaces):
                @staticmethod
                def get_interfaces() -> list[Electrical]:
                    return [self.CHANNELS]

            self.add_trait(_can_list_interfaces())

    class SPI(Interface):
        def __init__(self, cs_count, component) -> None:
            super().__init__()
            self.set_component(component)

            self.CS = [Electrical() for _ in range(cs_count)]
            self.MISO = Electrical()
            self.MOSI = Electrical()
            self.CLK = Electrical()
            self.GND = Electrical()

            class _can_list_interfaces(can_list_interfaces):
                @staticmethod
                def get_interfaces() -> list[Electrical]:
                    return [*self.CS, self.MISO, self.MOSI, self.CLK, self.GND]

            self.add_trait(_can_list_interfaces())

    class QSPI(Interface):
        def __init__(self, cs_count, component) -> None:
            super().__init__()
            self.set_component(component)

            self.D = Electrical()
            self.Q = Electrical()
            self.WP = Electrical()
            self.HD = Electrical()

            self.CS = [Electrical() for _ in range(cs_count)]

            self.CLK = Electrical()
            self.GND = Electrical()


            class _can_list_interfaces(can_list_interfaces):
                @staticmethod
                def get_interfaces() -> list[Electrical]:
                    return [*self.CS, self.D, self.Q, self.WP, self.HD, self.CLK, self.GND]

            self.add_trait(_can_list_interfaces())

    class ESP32_EMAC(Interface):
        def __init__(self, component) -> None:
            super().__init__()
            self.set_component(component)

            self.TXD            = [Electrical() for _ in range(4)]
            self.RXD            = [Electrical() for _ in range(4)]
            self.TX_CLK         = Electrical()
            self.RX_CLK         = Electrical()
            self.TX_EN          = Electrical()
            self.RX_ER          = Electrical()
            self.RX_DV          = Electrical()
            self.CLK_OUT        = Electrical()
            self.CLK_OUT_180    = Electrical()
            self.TX_ER          = Electrical()
            self.MDC_out        = Electrical()
            self.MDI_in         = Electrical()
            self.MDO_out        = Electrical()
            self.CRS_out        = Electrical()
            self.COL_out        = Electrical()

    class ESP32_SPI(Interface):
        def __init__(self, component) -> None:
            super().__init__()
            self.set_component(component)

            self.D = Electrical()
            self.Q = Electrical()
            self.WP = Electrical()
            self.HD = Electrical()

            self.CS = Electrical()

            self.CLK = Electrical()
            self.GND = Electrical()

            self.SPI = None # This will be set by configure I guess


        def configure(mode):
            #TODO has to build the correct SPI/DSPI/HSPI/QSPI interface and connect internally
            raise NotImplementedError()

    class ESP32(Component):
        def _setup_traits(self):
            self.add_trait(has_defined_type_description("ESP32"))

            class _has_footprint_pinmap(has_footprint_pinmap):
                def __init__(self, component: Component) -> None:
                    super().__init__()
                    self.component = component

                def get_pin_map(self):
                    component = self.component
                    return {
                        # Analog
                        1: component.VDDA0,
                        2: component.LNA_IN,
                        3: component.VDD3P30,
                        4: component.SENSOR_VP,
                        # VDD3P3_RTC
                        5: component.SENSOR_CAPP,
                        6: component.SENSOR_CAPN,
                        7: component.SENSOR_VN,
                        8: component.CHIP_PU,
                        9: component.VDET_1,
                        10: component.VDET_2,
                        11: component._32K_XP,
                        12: component._32K_XN,
                        13: component.GPIO25,
                        14: component.GPIO26,
                        15: component.GPIO27,
                        16: component.MTMS,
                        17: component.MTDI,
                        18: component.VDD3P3_RTC,
                        19: component.MTCK,
                        10: component.MTDO,
                        21: component.GPIO2,
                        22: component.GPIO0,
                        23: component.GPIO4,
                        # VDD_SDIO
                        24: component.GPIO16,
                        25: component.VDD_SDIO,
                        26: component.GPIO17,
                        27: component.SD_DATA_2,
                        28: component.SD_DATA_3,
                        29: component.SD_CMD,
                        30: component.SD_CLK,
                        31: component.SD_DATA_0,
                        32: component.SD_DATA_1,
                        # VDD3P3_CPU
                        33: component.GPIO5,
                        34: component.GPIO18,
                        35: component.GPIO23,
                        36: component.VDD3P3_CPU,
                        37: component.GPIO19,
                        38: component.GPIO22,
                        39: component.U0RXD,
                        40: component.U0TXD,
                        41: component.GPIO21,
                        # Analog
                        42: component.VDDA1,
                        43: component.XTAL_N,
                        44: component.XTAL_P,
                        45: component.VDDA2,
                        46: component.CAP2,
                        47: component.CAP1,
                        48: component.GND,
                    }
            self.add_trait(_has_footprint_pinmap(self))

        def _setup_interfaces(self):
            # Analog
            self.VDDA0          = Electrical()
            self.LNA_IN         = Electrical()
            self.VDD3P30        = Electrical()
            self.VDD3P31        = Electrical()
            self.SENSOR_VP      = Electrical()
            # VDD3P3_RTC
            self.SENSOR_CAPP    = Electrical()
            self.SENSOR_CAPN    = Electrical()
            self.SENSOR_VN      = Electrical()
            self.CHIP_PU        = Electrical()
            self.VDET_1         = Electrical()
            self.VDET_2         = Electrical()
            self._32K_XP        = Electrical()
            self._32K_XN        = Electrical()
            self.GPIO25         = Electrical()
            self.GPIO26         = Electrical()
            self.GPIO27         = Electrical()
            self.MTMS           = Electrical()
            self.MTDI           = Electrical()
            self.VDD3P3_RTC     = Electrical()
            self.MTCK           = Electrical()
            self.MTDO           = Electrical()
            self.GPIO2          = Electrical()
            self.GPIO0          = Electrical()
            self.GPIO4          = Electrical()
            # VDD_SDIO
            self.GPIO16         = Electrical()
            self.VDD_SDIO       = Electrical()
            self.GPIO17         = Electrical()
            self.SD_DATA_2      = Electrical()
            self.SD_DATA_3      = Electrical()
            self.SD_CMD         = Electrical()
            self.SD_CLK         = Electrical()
            self.SD_DATA_0      = Electrical()
            self.SD_DATA_1      = Electrical()
            # VDD3P3_CPU
            self.GPIO5          = Electrical()
            self.GPIO18         = Electrical()
            self.GPIO23         = Electrical()
            self.VDD3P3_CPU     = Electrical()
            self.GPIO19         = Electrical()
            self.GPIO22         = Electrical()
            self.U0RXD          = Electrical()
            self.U0TXD          = Electrical()
            self.GPIO21         = Electrical()
            # Analog
            self.VDDA1          = Electrical()
            self.XTAL_N         = Electrical()
            self.XTAL_P         = Electrical()
            self.VDDA2          = Electrical()
            self.CAP2           = Electrical()
            self.CAP1           = Electrical()
            self.GND            = Electrical()

            # High Level Functions
            self._FUNC_COMP     = None

            self.I2C            = [I2C(component=self._FUNC_COMP) for _ in range(2)]
            self.SDIO_SLAVE     = SDIO(component=self._FUNC_COMP)
            self.SDIO_HOST      = [None]+[SDIO(component=self._FUNC_COMP) for _ in range(2)]
            self.UART           = [UART(component=self._FUNC_COMP) for _ in range(1)]
            self.JTAG           = JTAG(component=self._FUNC_COMP)
            self.TOUCH          = [Electrical() for _ in range(10)]
            self.GPIO           = [Electrical() if x not in [20,24,28,29,30,31] else None for x in range(40)]
            self.RTC_GPIO       = [Electrical() for _ in range(18)]
            self.ADC            = [None, ADC(component=self._FUNC_COMP, channel_count=8), ADC(component=self, channel_count=10)]
            self.SPI            = [ESP32_SPI(component=self._FUNC_COMP) for _ in range(4)]
            self.EMAC           = ESP32_EMAC(component=self._FUNC_COMP)

            for interface in [*self.GPIO, *self.TOUCH, *self.RTC_GPIO]:
                if interface is None:
                    continue
                interface.set_component(self._FUNC_COMP)


            #SPI0 is connected to SPI1 (Arbiter)
            self.SPI[0].Q.connect(self.SPI[1].Q)
            self.SPI[0].D.connect(self.SPI[1].D)
            self.SPI[0].HD.connect(self.SPI[1].HD)
            self.SPI[0].WP.connect(self.SPI[1].WP)
            self.SPI[0].CLK.connect(self.SPI[1].CLK)
            self.SPI[0].CS.connect(self.SPI[1].CS)


            # TODO remove, this will happen in the pinmux
            #self.UART0.rx.connect(self.U0RXD)
            #self.UART0.tx.connect(self.U0TXD)
            #self.JTAG.MTDI.connect(self.MTDI)
            #self.JTAG.MTCK.connect(self.MTCK)
            #self.JTAG.MTMS.connect(self.MTMS)
            #self.JTAG.MTDO.connect(self.MTDO)
            #self.SDIO.SD0.connect(self.SD_DATA_0)
            #self.SDIO.SD1.connect(self.SD_DATA_1)
            #self.SDIO.SD2.connect(self.SD_DATA_2)
            #self.SDIO.SD3.connect(self.SD_DATA_3)
            #self.SDIO.CLK.connect(self.SD_CLK)
            #self.SDIO.CMD.connect(self.SD_CMD)

            #TODO the rest

            self.pinmux = ESP32_Pinmux(self)

        def _setup_power(self):
            self.power_rtc = Power()
            self.power_cpu = Power()
            self.power_sdio = Power()
            self.power_analog = Power()

            self.power_rtc.hv.connect(self.VDD3P3_RTC)
            self.power_rtc.lv.connect(self.GND)

            self.power_cpu.hv.connect(self.VDD3P3_CPU)
            self.power_cpu.lv.connect(self.GND)

            self.power_sdio.hv.connect(self.VDD_SDIO)
            self.power_sdio.lv.connect(self.GND)

            self.power_analog.hv.connect(self.VDDA0)
            self.power_analog.hv.connect(self.VDDA1)
            self.power_analog.hv.connect(self.VDDA2)
            self.power_analog.lv.connect(self.GND)

        def __new__(cls):
            self = super().__new__(cls)
            self._setup_traits()
            return self

        def __init__(self) -> None:
            super().__init__()
            self._setup_interfaces()
            self._setup_power()

    class ESP32_D0WD_V3(ESP32):
        # Dual core - No embedded flash/PSRAM
        def __init__(self):
            super().__init__()

        def __new__(cls):
            self = super().__new__(cls)

            ESP32._setup_traits(self)
            return self

        def _setup_traits(self):
            from faebryk.library.library.footprints import QFN
            self.add_trait(has_defined_footprint(QFN(
                pin_cnt=48,
                size_x_mm=5,
                size_y_mm=5,
            )))

    class ESP32_D0WDR2_V3(ESP32):
        # Dual core - 2 MB PSRAM
        def __init__(self):
            super().__init__()

        def __new__(cls):
            self = super().__new__(cls)

            ESP32._setup_traits(self)
            return self

        def _setup_traits(self):
            from faebryk.library.library.footprints import QFN
            self.add_trait(has_defined_footprint(QFN(
                pin_cnt=48,
                size_x_mm=5,
                size_y_mm=5,
            )))

    import typing
    @dataclass(frozen=True)
    class Function:
        interface: Interface
        name: str
        type: 'typing.Any'


    @dataclass(frozen=False)
    class Pad:
        no: int
        name: str
        interface: Interface
        power_domain: 'typing.Any'
        #
        at_reset: 'typing.Any'
        after_reset: 'typing.Any'
        drive_strenght: 'typing.Any'
        #
        functions: dict
        #
        current_function: Function = None

    class IsPinmuxed(InterfaceTrait):
        @abstractmethod
        def get_mux():
            raise NotImplementedError()

        def connect_and_mux(self, interface: Interface):
            self.ref.connect(interface)
            self.get_mux().mux_if(self.ref)

    class IsPinmuxedTo(IsPinmuxed):
        def __init__(self, pinmux) -> None:
            super().__init__()
            self.pinmux = pinmux

        def get_mux(self):
            return self.pinmux

    class ESP32_Pinmux:
        def __init__(self, esp32: ESP32) -> None:
            default_function = 5
            self.matrix = [
                # Power
                Pad(1,  "VDDA",         esp32.VDDA0,        "VDDA supply in",           None, None, None, {}),
                Pad(43, "VDDA",         esp32.VDDA1,        "VDDA supply in",           None, None, None, {}),
                Pad(46, "VDDA",         esp32.VDDA2,        "VDDA supply in",           None, None, None, {}),
                Pad(2,  "LNA_IN",       esp32.LNA_IN,       "VDD3P3",                   None, None, None, {}),
                Pad(3,  "VDD3P3",       esp32.VDD3P30,      "VDD3P3 supply in",         None, None, None, {}),
                Pad(4,  "VDD3P3",       esp32.VDD3P31,      "VDD3P3 supply in",         None, None, None, {}),
                Pad(19, "VDD3P3_RTC",   esp32.VDD3P3_RTC,   "VDD3P3_RTC supply in",     None, None, None, {}),
                Pad(26, "VDD_SDIO",     esp32.VDD_SDIO,     "VDD_SDIO supply out/in",   None, None, None, {}),
                Pad(37, "VDD3P3_CPU",   esp32.VDD3P3_CPU,   "VDD3P3_CPU supply in",     None, None, None, {}),

                #
                Pad(5,  "SENSOR_VP",    esp32.SENSOR_VP,    "VDD3P3_RTC", "oe=0,ie=0", "oe=0,ie=0", None, {
                    1 : Function(esp32.ADC[1].CHANNELS[0],  "ADC1_CH0",   None),
                    3 : Function(esp32.RTC_GPIO[0],         "RTC_GPIO0",  None),
                    5 : Function(esp32.GPIO[36],            "GPIO36",     "I"),
                }),
                Pad(6,  "SENSOR_CAPP", esp32.SENSOR_CAPP,   "VDD3P3_RTC", "oe=0,ie=0", "oe=0,ie=0", None, {
                    1 : Function(esp32.ADC[1].CHANNELS[1],  "ADC1_CH1",   None),
                    3 : Function(esp32.RTC_GPIO[1],         "RTC_GPIO1",  None),
                    5 : Function(esp32.GPIO[37],            "GPIO37",     "I"),
                }),
                Pad(7,  "SENSOR_CAPN", esp32.SENSOR_CAPN,   "VDD3P3_RTC", "oe=0,ie=0", "oe=0,ie=0", None, {
                    1 : Function(esp32.ADC[1].CHANNELS[2],  "ADC1_CH2",   None),
                    3 : Function(esp32.RTC_GPIO[2],         "RTC_GPIO2",  None),
                    5 : Function(esp32.GPIO[38],            "GPIO38",     "I"),
                }),
                Pad(18,  "MTDI",       esp32.MTDI,          "VDD3P3_RTC", "oe=0,ie=1,wpd", "oe=0,ie=1,wpd", "2'd2", {
                    1 : Function(esp32.ADC[2].CHANNELS[5],  "ADC2_CH5",   None),
                    2 : Function(esp32.TOUCH[5],            "TOUCH5",     None),
                    3 : Function(esp32.RTC_GPIO[15],        "RTC_GPIO15", None),
                    5 : Function(esp32.JTAG.MTDI,           "MTDI",       "I1"),
                    6 : Function(esp32.SPI[2].Q,            "HSPIQ",      "I/O/T"),
                    7 : Function(esp32.GPIO[12],            "GPIO12",     "I/O/T"),
                    8 : Function(esp32.SDIO_HOST[2].DATA[2],"HS2_DATA2",  "I1/O/T"),
                    9 : Function(esp32.SDIO_SLAVE.DATA[2],  "SD_DATA2",   "I1/O/T"),
                    10: Function(esp32.EMAC.TXD[3],         "EMAC_TXD3",  "O"),
                }),
            ]

            for pad in self.matrix:
                for function in pad.functions.values():
                    function.interface.add_trait(IsPinmuxedTo(self))

            for pad in self.matrix:
                if len(pad.functions.items()) == 0:
                    continue
                self._mux(pad.functions[default_function], pad)

        def _mux(self, function: Function, pad: Pad):
            if pad.current_function == function:
                return

            # Check if already set
            # TODO remove, and make sure that reconnection is legal or spit warning or so
            #assert (pad.current_function == None), "Already set"

            pad.current_function = function
            function.interface.connect(pad.interface)

        def mux(self, internal: Interface, pad: Interface):
            # Check if combination legal
            row = [pin for pin in self.matrix if pin.interface == pad][0]
            col = [function for function in row.values() if function.interface == internal][0]

            self._mux(col, row)

        def mux_if(self, internal: Interface):
            for pad in self.matrix:
                for function in pad.functions.values():
                    if function.interface == internal:
                        self._mux(function, pad)
                        return
            assert (False), "Not a pinmux interface"

        def mux_peripheral(self, peripheral: Interface):
            ifs = peripheral.get_trait(can_list_interfaces).get_interfaces()
            for interface in ifs:
                self.mux_if(interface)

    # power
    gnd = Electrical()

    soc = ESP32_D0WDR2_V3()
    led = LED()
    current_limiting_resistor = Resistor(TBD())

    current_limiting_resistor.interfaces[1].connect(gnd)
    soc.GND.connect(gnd)

    led.set_forward_parameters(
        voltage_V=Constant(2.4),
        current_A=Constant(0.020)
    )
    current_limiting_resistor.set_resistance(led.get_trait(LED.has_calculatable_needed_series_resistance).get_needed_series_resistance_ohm(5))
    led.cathode.connect(current_limiting_resistor.interfaces[0])
    for smd in [led, current_limiting_resistor]:
        smd.add_trait(has_defined_footprint(SMDTwoPin(SMDTwoPin.Type._0805)))
    led.add_trait(has_defined_footprint_pinmap({
        1: led.anode,
        2: led.cathode,
    }))
    current_limiting_resistor.add_trait(has_symmetric_footprint_pinmap(current_limiting_resistor))


    soc.GPIO[12].get_trait(IsPinmuxed).connect_and_mux(led.anode)

    comps = [
        soc,
        led,
        current_limiting_resistor
    ]

    t1_ = make_t1_netlist_from_graph(
            make_graph_from_components(comps)
        )

    netlist = from_faebryk_t2_netlist(
        make_t2_netlist_from_t1(
            t1_
        )
    )

    print("Experiment netlist:")
    print(netlist)

    from faebryk.exporters.netlist import render_graph
    render_graph(t1_)

# Boilerplate -----------------------------------------------------------------
import sys
import logging

def main(argc, argv, argi):
    logging.basicConfig(level=logging.INFO)

    print("Running experiment")
    run_experiment()

if __name__ == "__main__":
    import os
    import sys
    root = os.path.join(os.path.dirname(__file__), '..')
    sys.path.append(root)
    main(len(sys.argv), sys.argv, iter(sys.argv))
