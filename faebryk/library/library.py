# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

from __future__ import annotations
from enum import Enum
from typing import Iterable

from faebryk.library.core import *
from faebryk.library.traits import *
from faebryk.libs.exceptions import FaebrykException

import logging
logger = logging.getLogger("library")

# Parameter -------------------------------------------------------------------
class Constant(Parameter):
    def __init__(self, value: typing.Any) -> None:
        super().__init__()
        self.value = value
        self.add_trait(is_representable_by_single_value(
            self.value
        ))

class TBD(Parameter):
    def __init__(self) -> None:
        super().__init__()
# -----------------------------------------------------------------------------

# Footprints ------------------------------------------------------------------
class DIP(Footprint):
    def __init__(self, pin_cnt: int, spacing_mm: int, long_pads: bool) -> None:
        super().__init__()

        class _has_kicad_footprint(has_kicad_footprint):
            @staticmethod
            def get_kicad_footprint() -> str:
                return \
                    "DIP-{leads}-W{spacing:.2f}mm{longpads}".format(
                        leads=pin_cnt,
                        spacing=spacing_mm,
                        longpads="_LongPads" if long_pads else ""
                    )

        self.add_trait(_has_kicad_footprint())

class SMDTwoPin(Footprint):
    class Type(Enum):
        _01005 = 0 
        _0201  = 1
        _0402  = 2
        _0603  = 3
        _0805  = 4
        _1206  = 5
        _1210  = 6
        _1218  = 7
        _2010  = 8
        _2512  = 9

    def __init__(self, type: Type) -> None:
        super().__init__()

        class _has_kicad_footprint(has_kicad_footprint):
            @staticmethod
            def get_kicad_footprint() -> str:
                table = {
                    self.Type._01005: "0402",
                    self.Type._0201:  "0603",
                    self.Type._0402:  "1005",
                    self.Type._0603:  "1005",
                    self.Type._0805:  "2012",
                    self.Type._1206:  "3216",
                    self.Type._1210:  "3225",
                    self.Type._1218:  "3246",
                    self.Type._2010:  "5025",
                    self.Type._2512:  "6332",
                } 

                return \
                    "R_{imperial}_{metric}Metric.kicad_mod".format(
                        imperial=type.name[1:],
                        metric=table[type]
                    )
                
        self.add_trait(_has_kicad_footprint())
# ------------------------------------------------------------------------

# Interfaces ------------------------------------------------------------------
class Electrical(Interface):
    def __init__(self) -> None:
        super().__init__()

        class _can_list_interfaces(can_list_interfaces):
            @staticmethod
            def get_interfaces() -> list(Electrical):
                return [self]

        class _contructable_from_interface_list(contructable_from_interface_list):
            @staticmethod
            def from_interfaces(interfaces: Iterable(Electrical)) -> Electrical:
                return next(interfaces)

        self.add_trait(_can_list_interfaces())
        self.add_trait(_contructable_from_interface_list())

class Power(Interface):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)

        self.hv = Electrical()
        self.lv = Electrical()

        self.set_component(kwargs.get("component"))

        class _can_list_interfaces(can_list_interfaces):
            @staticmethod
            def get_interfaces() -> list(Electrical):
                return [self.hv, self.lv]

        class _contructable_from_interface_list(contructable_from_interface_list):
            @staticmethod
            def from_interfaces(interfaces: Iterable(Electrical)) -> Power:
                p = Power()
                p.hv = next(interfaces)
                p.lv = next(interfaces)

                comps = get_components_of_interfaces(p.get_trait(can_list_interfaces).get_interfaces())
                assert (len(comps) < 2 or comps[0] == comps[1])
                if len(comps) > 0:
                    p.set_component(comps[0])

                return p
        
        self.add_trait(_can_list_interfaces())
        self.add_trait(_contructable_from_interface_list())

        #TODO finish the trait stuff
#        self.add_trait(is_composed([self.hv, self.lv]))


#class I2C(Interface):
#    def __init__(self) -> None:
#        super().__init__()
#        self.sda = Electrical()
#        self.sdc = Electrical()
#        self.gnd = Electrical()
#        self.add_trait(is_composed(
#            [self.sda, self.sdc, self.gnd]
#        ))
# -----------------------------------------------------------------------------


# Links -----------------------------------------------------------------------
# -----------------------------------------------------------------------------

#class Component:
#    def __init__(self, name, pins, real):
#        self.comp = {
#            "name": name,
#            "properties": {
#            },
#            "real": real,
#            "neighbors": {pin: [] for pin in pins}
#        }
#        self.pins = pins
#
#    def connect(self, spin, other, dpin=None):
#        self.comp["neighbors"][spin].append({
#            "vertex": other.get_comp(),
#            "pin": dpin,
#        })

# META SHIT -------------------------------------------------------------------
def default_with(given, default):
    if given is not None:
        return given
    return default

def times(cnt, lamb):
    return [lamb() for _ in range(cnt)]

def unit_map(value: int, units, start=None, base=1000):
    if start is None:
        start_idx = 0
    else:
        start_idx = units.index(start)
    
    cur = base**((-start_idx)+1)
    ptr = 0
    while value >= cur:
        cur *= base
        ptr += 1
    form_value = integer_base(value, base=base)
    return f"{form_value}{units[ptr]}"

def integer_base(value: int, base=1000):
    while value < 1:
        value *= base
    while value >= base:
        value /= base
    return value

def get_all_interfaces(interfaces : Iterable(Interface)) -> list(Interface):
    return [
        nested for i in interfaces 
            for nested in i.get_trait(can_list_interfaces).get_interfaces()
    ]

def get_components_of_interfaces(interfaces: list(Interface)) -> list(Component):
    out = [
        i.get_trait(is_part_of_component).get_component() for i in interfaces
            if i.has_trait(is_part_of_component)
    ]
    return out

# -----------------------------------------------------------------------------

# Components ------------------------------------------------------------------
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
        self.inputs = [Electrical().get_trait(contructable_from_interface_list).from_interfaces(it) for i in n.inputs]

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
            def from_nands(nands : list(NAND)) -> CD4011:
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
            n.output.connect(target)
            self.connection_map[n.output] = target

            for i in n.inputs:
                target = next(it)
                i.connect(target)
                self.connection_map[i] = target

        #TODO
        #assert(len(self.interfaces) == 14)

    def __new__(cls):
        self = super().__new__(cls)

        self._setup_traits()
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

    def _init_from_nands(self, nands : list(NAND)):
        # checks
        assert(len(nands) <= 4)
        nands += times(4-len(nands), lambda: NAND(input_cnt=2))
        

        for nand in nands:
            assert(nand.input_cnt == 2)
        
        # setup
        self._setup_power()
        self.nands = nands
        self._setup_inouts()
        self._setup_internal_connections()


        
# -----------------------------------------------------------------------------
