# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging
from faebryk.library.traits import component

from faebryk.library.traits.component import contructable_from_component, has_defined_footprint, has_defined_footprint_pinmap, has_defined_type_description, has_footprint_pinmap, has_interfaces, has_interfaces_list, has_symmetric_footprint_pinmap, has_type_description
from faebryk.library.traits.interface import contructable_from_interface_list
logger = logging.getLogger("library")

from faebryk.library.core import Component, ComponentTrait, Interface, Parameter
from faebryk.library.library.interfaces import Electrical, Power
from faebryk.library.library.parameters import Constant
from faebryk.library.traits import *
from faebryk.library.util import get_all_interfaces, times, unit_map

class Resistor(Component):
    def _setup_traits(self):
        class _contructable_from_component(contructable_from_component):
            @staticmethod
            def from_component(comp: Component, resistance: Parameter) -> Resistor:
                assert(comp.has_trait(has_interfaces))
                interfaces = comp.get_trait(has_interfaces).get_interfaces()
                assert(len(interfaces) == 2)
                assert(len([i for i in interfaces if type(i) is not Electrical]) == 0)

                r = Resistor.__new__(Resistor)
                r._setup_resistance(resistance)
                r.interfaces = interfaces
                r.get_trait(has_interfaces).set_interface_comp(r)

                return r

        self.add_trait(has_interfaces_list(self))
        self.add_trait(_contructable_from_component())

    def _setup_interfaces(self):
        self.interfaces = times(2, Electrical)
        self.get_trait(has_interfaces).set_interface_comp(self)

    def __new__(cls, *args, **kwargs):
        self = super().__new__(cls)
        self._setup_traits()
        return self

    def __init__(self, resistance : Parameter):
        super().__init__()

        self._setup_interfaces()
        self.set_resistance(resistance)

    def set_resistance(self, resistance: Parameter):
        self.resistance = resistance

        if type(resistance) is not Constant:
            #TODO this is a bit ugly
            # it might be that there was another more abstract valid trait
            # but this challenges the whole trait overriding mechanism
            # might have to make a trait stack thats popped or so
            self.del_trait(has_type_description)
            return

        class _has_type_description(has_type_description):
            @staticmethod
            def get_type_description():
                resistance = self.resistance
                return unit_map(resistance.value, ["µΩ", "mΩ", "Ω", "KΩ", "MΩ", "GΩ"], start="Ω")
        self.add_trait(_has_type_description())

class LED(Component):

    class has_calculatable_needed_series_resistance(ComponentTrait):
        @staticmethod
        def get_needed_series_resistance_ohm(input_voltage_V) -> int:
            raise NotImplemented

    def _setup_traits(self):
        class _has_interfaces(has_interfaces):
            @staticmethod
            def get_interfaces() -> list[Interface]:
                return [self.anode, self.cathode]

        self.add_trait(has_defined_type_description("LED"))
        self.add_trait(_has_interfaces())

    def _setup_interfaces(self):
        self.anode = Electrical()
        self.cathode = Electrical()
        self.get_trait(has_interfaces).set_interface_comp(self)

    def __new__(cls):
        self = super().__new__(cls)
        self._setup_traits()
        return self

    def __init__(self) -> None:
        super().__init__()
        self._setup_interfaces()

    def set_forward_parameters(self, voltage_V: Parameter, current_A: Parameter):
        if type(voltage_V) is Constant and type(current_A) is Constant:
            class _(self.has_calculatable_needed_series_resistance):
                @staticmethod
                def get_needed_series_resistance_ohm(input_voltage_V) -> int:
                    return LED.needed_series_resistance_ohm(
                        input_voltage_V,
                        voltage_V.value,
                        current_A.value
                    )
            self.add_trait(_())


    @staticmethod
    def needed_series_resistance_ohm(input_voltage_V, forward_voltage_V, forward_current_A) -> Constant:
        return Constant((input_voltage_V-forward_voltage_V)/forward_current_A)

class Switch(Component):
    def _setup_traits(self):
        self.add_trait(has_defined_type_description("SW"))
        self.add_trait(has_interfaces_list(self))

    def _setup_interfaces(self):
        self.interfaces = times(2, Electrical)
        self.get_trait(has_interfaces).set_interface_comp(self)

    def __new__(cls):
        self = super().__new__(cls)
        self._setup_traits()
        return self

    def __init__(self) -> None:
        super().__init__()
        self._setup_interfaces()

class NAND(Component):
    def _setup_traits(self):
        class _has_interfaces(has_interfaces):
            @staticmethod
            def get_interfaces():
                return get_all_interfaces([self.power, self.output, *self.inputs])

        class _constructable_from_component(contructable_from_component):
            @staticmethod
            def from_comp(comp: Component) -> NAND:
                n = NAND.__new__(NAND)
                n.__init_from_comp(comp)
                return n

        self.add_trait(_has_interfaces())
        self.add_trait(_constructable_from_component())

    def _setup_power(self):
        self.power = Power()

    def _setup_inouts(self, input_cnt):
        self.output = Electrical()
        self.inputs = times(input_cnt, Electrical)
        self._set_interface_comp()

    def _set_interface_comp(self):
        self.get_trait(has_interfaces).set_interface_comp(self)

    def __new__(cls, *args, **kwargs):
        self = super().__new__(cls)

        self._setup_traits()

        return self

    def __init__(self, input_cnt: int):
        super().__init__()

        self._setup_power()
        self._setup_inouts(input_cnt)

        self.input_cnt = input_cnt

    def __init_from_comp(self, comp: Component):
        dummy = NAND(2)
        base_cnt = len(get_all_interfaces(dummy))

        assert(comp.has_trait(has_interfaces))
        interfaces = comp.get_trait(has_interfaces).get_interfaces()
        assert(len(interfaces) >= base_cnt)
        assert(len([i for i in interfaces if type(i) is not Electrical]) == 0)

        it = iter(interfaces)

        self.power = Power().get_trait(contructable_from_interface_list).from_interfaces(it)
        self.output = Electrical().get_trait(contructable_from_interface_list).from_interfaces(it)
        self.inputs = [Electrical().get_trait(contructable_from_interface_list).from_interfaces(it) for i in self.inputs]

        self.input_cnt = len(self.inputs)
        self._set_interface_comp()

class CD4011(Component):
    class constructable_from_nands(ComponentTrait):
        @staticmethod
        def from_comp(comp: Component):
            raise NotImplemented


    def _setup_traits(self):
        class _has_interfaces(has_interfaces):
            @staticmethod
            def get_interfaces():
                return get_all_interfaces([self.power, *self.in_outs])

        class _constructable_from_component(contructable_from_component):
            @staticmethod
            def from_comp(comp: Component) -> CD4011:
                c = CD4011.__new__(CD4011)
                c._init_from_comp(comp)
                return c

        class _constructable_from_nands(self.constructable_from_nands):
            @staticmethod
            def from_nands(nands : list[NAND]) -> CD4011:
                c = CD4011.__new__(CD4011)
                c._init_from_nands(nands)
                return c


        self.add_trait(_has_interfaces())
        self.add_trait(_constructable_from_component())
        self.add_trait(_constructable_from_nands())
        self.add_trait(has_defined_type_description("cd4011"))


    def _setup_power(self):
        self.power = Power()

    def _setup_nands(self):
        self.nands = times(4, lambda: NAND(input_cnt=2))
        for n in self.nands:
            n.add_trait(has_symmetric_footprint_pinmap(n))

    def _setup_inouts(self):
        nand_inout_interfaces = [i for n in self.nands for i in get_all_interfaces([n.output, *n.inputs])]
        self.in_outs = times(len(nand_inout_interfaces), Electrical)

    def _setup_internal_connections(self):
        self.get_trait(has_interfaces).set_interface_comp(self)

        self.connection_map = {}

        it = iter(self.in_outs)
        for n in self.nands:
            n.power.connect(self.power)
            target = next(it)
            target.connect(n.output)
            self.connection_map[n.output] = target

            for i in n.inputs:
                target = next(it)
                target.connect(i)
                self.connection_map[i] = target

        #TODO
        #assert(len(self.interfaces) == 14)

    def __new__(cls):
        self = super().__new__(cls)

        CD4011._setup_traits(self)
        return self

    def __init__(self):
        super().__init__()

        # setup
        self._setup_power()
        self._setup_nands()
        self._setup_inouts()
        self._setup_internal_connections()

    def _init_from_comp(self, comp: Component):
        # checks
        assert(comp.has_trait(has_interfaces))
        interfaces = comp.get_trait(has_interfaces).get_interfaces()
        assert(len(interfaces) == len(self.get_trait(has_interfaces).get_interfaces()))
        assert(len([i for i in interfaces if type(i) is not Electrical]) == 0)

        it = iter(interfaces)

        # setup
        self.power = Power().get_trait(contructable_from_interface_list).from_interfaces(it)
        self._setup_nands()
        self.in_outs = [Electrical().get_trait(contructable_from_interface_list).from_interfaces(i) for i in it]
        self._setup_internal_connections()

    def _init_from_nands(self, nands : list[NAND]):
        # checks
        assert(len(nands) <= 4)
        cd_nands = list(nands)
        cd_nands += times(4-len(cd_nands), lambda: NAND(input_cnt=2))


        for nand in cd_nands:
            assert(nand.input_cnt == 2)

        # setup
        self._setup_power()
        self.nands = cd_nands
        self._setup_inouts()
        self._setup_internal_connections()

class TI_CD4011BE(CD4011):
    def __init__(self):
        super().__init__()
    
    def __new__(cls):
        self = super().__new__(cls)

        TI_CD4011BE._setup_traits(self)
        return self

    def _setup_traits(self):
        from faebryk.library.library.footprints import DIP
        self.add_trait(has_defined_footprint(DIP(
            pin_cnt=14, 
            spacing_mm=7.62, 
            long_pads=False
        )))

        class _has_footprint_pinmap(has_footprint_pinmap):
            def __init__(self, component: Component) -> None:
                super().__init__()
                self.component = component

            def get_pin_map(self):
                component = self.component
                return {
                    7:  component.power.lv,
                    14: component.power.hv,
                    3:  component.connection_map[component.nands[0].output],
                    4:  component.connection_map[component.nands[1].output],
                    11: component.connection_map[component.nands[2].output],
                    10: component.connection_map[component.nands[3].output],
                    1:  component.connection_map[component.nands[0].inputs[0]],
                    2:  component.connection_map[component.nands[0].inputs[1]],
                    5:  component.connection_map[component.nands[1].inputs[0]],
                    6:  component.connection_map[component.nands[1].inputs[1]],
                    12: component.connection_map[component.nands[2].inputs[0]],
                    13: component.connection_map[component.nands[2].inputs[1]],
                    9:  component.connection_map[component.nands[3].inputs[0]],
                    8:  component.connection_map[component.nands[3].inputs[1]],
                }

        self.add_trait(_has_footprint_pinmap(self))
