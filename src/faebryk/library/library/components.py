# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging

from faebryk.library.library.footprints import (
    DIP,
    can_attach_to_footprint_symmetrically,
    can_attach_via_pinmap,
)
from faebryk.library.trait_impl.component import (
    can_bridge_defined,
    has_defined_footprint,
    has_defined_type_description,
)
from faebryk.library.traits.component import has_type_description

logger = logging.getLogger(__name__)

from faebryk.library.core import Module, NodeTrait, Parameter
from faebryk.library.library.interfaces import Electrical, ElectricPower
from faebryk.library.library.parameters import TBD, Constant
from faebryk.library.util import connect_to_all_interfaces, times, unit_map


class Resistor(Module):
    def _setup_traits(self):
        class _has_type_description(has_type_description.impl()):
            @staticmethod
            def get_type_description():
                assert isinstance(self.resistance, Constant)
                resistance: Constant = self.resistance
                return unit_map(
                    resistance.value, ["µΩ", "mΩ", "Ω", "KΩ", "MΩ", "GΩ"], start="Ω"
                )

            def is_implemented(self):
                c = self.get_obj()
                assert isinstance(c, Resistor)
                return type(c.resistance) is Constant

        self.add_trait(_has_type_description())
        self.add_trait(can_attach_to_footprint_symmetrically())

    def _setup_interfaces(self):
        class _IFs(super().IFS()):
            unnamed = times(2, Electrical)

        self.IFs = _IFs(self)

        self.add_trait(can_bridge_defined(*self.IFs.unnamed))

    def __new__(cls, *args, **kwargs):
        self = super().__new__(cls)
        self._setup_traits()
        return self

    def __init__(self, resistance: Parameter):
        super().__init__()

        self._setup_interfaces()
        self.set_resistance(resistance)

    def set_resistance(self, resistance: Parameter):
        self.resistance = resistance


class Capacitor(Module):
    def __new__(cls, *args, **kwargs):
        self = super().__new__(cls)
        self._setup_traits()
        return self

    def __init__(self, capacitance: Parameter):
        super().__init__()

        self._setup_interfaces()
        self.set_capacitance(capacitance)

    def _setup_traits(self):
        class _has_type_description(has_type_description.impl()):
            @staticmethod
            def get_type_description():
                assert isinstance(self.capacitance, Constant)
                return unit_map(
                    self.capacitance.value,
                    ["µF", "mF", "F", "KF", "MF", "GF"],
                    start="F",
                )

            def is_implemented(self):
                c = self.get_obj()
                assert isinstance(c, Capacitor)
                return type(c.capacitance) is Constant

        self.add_trait(_has_type_description())

    def _setup_interfaces(self):
        class _IFs(super().IFS()):
            unnamed = times(2, Electrical)

        self.IFs = _IFs(self)
        self.add_trait(can_bridge_defined(*self.IFs.unnamed))

    def set_capacitance(self, capacitance: Parameter):
        self.capacitance = capacitance


class BJT(Module):
    def __new__(cls):
        self = super().__new__(cls)
        self._setup_traits()
        return self

    def __init__(self) -> None:
        super().__init__()
        self._setup_interfaces()

    def _setup_traits(self):
        self.add_trait(has_defined_type_description("BJT"))

    def _setup_interfaces(self):
        class _IFs(super().IFS()):
            emitter = Electrical()
            base = Electrical()
            collector = Electrical()

        self.IFs = _IFs(self)


class MOSFET(Module):
    def __new__(cls):
        self = super().__new__(cls)
        self._setup_traits()
        return self

    def __init__(self) -> None:
        super().__init__()
        self._setup_interfaces()

    def _setup_traits(self):
        self.add_trait(has_defined_type_description("MOSFET"))

    def _setup_interfaces(self):
        class _IFs(super().IFS()):
            source = Electrical()
            gate = Electrical()
            drain = Electrical()

        self.IFs = _IFs(self)


class LED(Module):
    class has_calculatable_needed_series_resistance(NodeTrait):
        @staticmethod
        def get_needed_series_resistance_ohm(input_voltage_V: float) -> Constant:
            raise NotImplemented

    def _setup_traits(self):
        self.add_trait(has_defined_type_description("LED"))

        class _(self.has_calculatable_needed_series_resistance.impl()):
            @staticmethod
            def get_needed_series_resistance_ohm(
                input_voltage_V: float,
            ) -> Constant:
                assert isinstance(self.voltage_V, Constant)
                assert isinstance(self.current_A, Constant)

                return LED.needed_series_resistance_ohm(
                    input_voltage_V, self.voltage_V.value, self.current_A.value
                )

            def is_implemented(self):
                obj = self.get_obj()
                assert isinstance(obj, LED)
                return isinstance(obj.voltage_V, Constant) and isinstance(
                    obj.current_A, Constant
                )

        self.add_trait(_())

    def _setup_interfaces(self):
        class _IFs(super().IFS()):
            anode = Electrical()
            cathode = Electrical()

        self.IFs = _IFs(self)

    def __new__(cls):
        self = super().__new__(cls)
        self._setup_traits()
        return self

    def __init__(self) -> None:
        super().__init__()
        self._setup_interfaces()
        self.set_forward_parameters(TBD(), TBD())

    def set_forward_parameters(self, voltage_V: Parameter, current_A: Parameter):
        self.voltage_V = voltage_V
        self.current_A = current_A

    @staticmethod
    def needed_series_resistance_ohm(
        input_voltage_V: float, forward_voltage_V: float, forward_current_A: float
    ) -> Constant:
        return Constant(int((input_voltage_V - forward_voltage_V) / forward_current_A))


class Potentiometer(Module):
    def __new__(cls, *args, **kwargs):
        self = super().__new__(cls, *args, **kwargs)
        self._setup_traits()
        return self

    def __init__(self, resistance: Parameter) -> None:
        super().__init__()
        self._setup_interfaces(resistance)

    def _setup_traits(self):
        pass

    def _setup_interfaces(self, resistance):
        class _IFs(super().IFS()):
            resistors = times(2, Electrical)
            wiper = Electrical()

        class _NODEs(super().NODES()):
            resistors = [Resistor(resistance) for _ in range(2)]

        self.IFs = _IFs(self)
        self.NODEs = _NODEs(self)

        connect_to_all_interfaces(
            self.IFs.wiper,
            [
                self.NODEs.resistors[0].IFs.unnamed[1],
                self.NODEs.resistors[1].IFs.unnamed[1],
            ],
        )

        for i, resistor in enumerate(self.NODEs.resistors):
            self.IFs.resistors[i].connect(resistor.IFs.unnamed[0])

    def connect_as_voltage_divider(self, high, low, out):
        self.IFs.resistors[0].connect(high)
        self.IFs.resistors[1].connect(low)
        self.IFs.wiper.connect(out)


class Switch(Module):
    def _setup_traits(self):
        self.add_trait(has_defined_type_description("SW"))
        self.add_trait(can_attach_to_footprint_symmetrically())

    def _setup_interfaces(self):
        class _IFs(super().IFS()):
            unnamed = times(2, Electrical)

        self.IFs = _IFs(self)
        self.add_trait(can_bridge_defined(*self.IFs.unnamed))

    def __new__(cls):
        self = super().__new__(cls)
        self._setup_traits()
        return self

    def __init__(self) -> None:
        super().__init__()
        self._setup_interfaces()


class PJ398SM(Module):
    def __new__(cls):
        self = super().__new__(cls)
        self._setup_traits()
        return self

    def __init__(self) -> None:
        super().__init__()
        self._setup_interfaces()

    def _setup_traits(self):
        self.add_trait(has_defined_type_description("Connector"))

    def _setup_interfaces(self):
        class _IFs(super().IFS()):
            tip = Electrical()
            sleeve = Electrical()
            switch = Electrical()

        self.IFs = _IFs(self)


class NAND(Module):
    def _setup_traits(self):
        pass

    def _setup_interfaces(self, input_cnt):
        # TODO
        # constraint: cant connect to outside
        class _NODEs(super().NODES()):
            power = ElectricPower()

        self.NODEs = _NODEs(self)

        # self.IFs.external_children.connect(self.NODEs.power.IFs.parent)
        class _IFNODEs(super().NODES()):
            power = ElectricPower()

        self.IFNODEs = _IFNODEs(self)

        class _IFs(super().IFS()):
            output = Electrical()
            inputs = times(input_cnt, Electrical)
            power = ElectricPower()

        self.IFs = _IFs(self)

        self.IFNODEs.power.connect

    def __new__(cls, *args, **kwargs):
        self = super().__new__(cls)

        self._setup_traits()

        return self

    def __init__(self, input_cnt: int):
        super().__init__()

        self._setup_interfaces(input_cnt)


class CD4011(Module):
    def _setup_traits(self):
        self.add_trait(has_defined_type_description("cd4011"))

    @classmethod
    def NODES(cls):
        class NODES(Module.NODES()):
            nands = times(4, lambda: NAND(input_cnt=2))

        return NODES

    def _setup_nands(self):
        self.NODEs = CD4011.NODES()(self)

    def _setup_interfaces(self):
        nand_inout_interfaces = [
            i for n in self.NODEs.nands for i in [n.IFs.output, *n.IFs.inputs]
        ]

        class _IFs(super().IFS()):
            power = ElectricPower()
            in_outs = times(len(nand_inout_interfaces), Electrical)

        self.IFs = _IFs(self)

    def _setup_internal_connections(self):
        it = iter(self.IFs.in_outs)
        for n in self.NODEs.nands:
            n.IFs.power.connect(self.IFs.power)
            target = next(it)
            target.connect(n.IFs.output)

            for i in n.IFs.inputs:
                target = next(it)
                target.connect(i)

        # TODO
        # assert(len(self.interfaces) == 14)

    def __new__(cls):
        self = super().__new__(cls)

        CD4011._setup_traits(self)
        return self

    def __init__(self):
        super().__init__()

        # setup
        self._setup_nands()
        self._setup_interfaces()
        self._setup_internal_connections()


class TI_CD4011BE(CD4011):
    def __init__(self):
        super().__init__()

        fp = DIP(pin_cnt=14, spacing_mm=7.62, long_pads=False)
        self.add_trait(has_defined_footprint(fp))
        fp.get_trait(can_attach_via_pinmap).attach(
            {
                "7": self.IFs.power.NODEs.lv,
                "14": self.IFs.power.NODEs.hv,
                "3": self.NODEs.nands[0].IFs.output,
                "4": self.NODEs.nands[1].IFs.output,
                "11": self.NODEs.nands[2].IFs.output,
                "10": self.NODEs.nands[3].IFs.output,
                "1": self.NODEs.nands[0].IFs.inputs[0],
                "2": self.NODEs.nands[0].IFs.inputs[1],
                "5": self.NODEs.nands[1].IFs.inputs[0],
                "6": self.NODEs.nands[1].IFs.inputs[1],
                "12": self.NODEs.nands[2].IFs.inputs[0],
                "13": self.NODEs.nands[2].IFs.inputs[1],
                "9": self.NODEs.nands[3].IFs.inputs[0],
                "8": self.NODEs.nands[3].IFs.inputs[1],
            }
        )
