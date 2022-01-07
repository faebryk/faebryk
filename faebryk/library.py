# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

from typing import Any, Iterable
from faebryk.libs.exceptions import FaebrykException
import typing

import logging
logger = logging.getLogger("library")

# 1st order classes -----------------------------------------------------------
class Trait:
    def __eq__(self, other: Trait) -> bool:
        return type(self) is other

class FaebrykLibObject:
    def __init__(self) -> None:
        #TODO maybe dict[class => [obj]
        self.traits = []

    def add_trait(self, trait : Trait) -> None:
        if type(trait) not in self.traits:
            self.traits.append(trait)
            return

        self.traits[self.traits.index(type(trait))] = trait

    def has_trait(self, trait) -> bool:
        #return any(lambda t: type(t) is trait, self.traits)
        return trait in self.traits

    def get_trait(self, trait):
        return self.traits[self.traits.index(trait)]
        
# -----------------------------------------------------------------------------

# Traits ----------------------------------------------------------------------
class FootprintTrait(Trait):
    pass

class InterfaceTrait(Trait):
    pass

class ComponentTrait(Trait):
    pass

class LinkTrait(Trait):
    pass

class ParameterTrait(Trait):
    pass
# -----------------------------------------------------------------------------

# FaebrykLibObjects -----------------------------------------------------------
class Footprint(FaebrykLibObject):
    def __init__(self) -> None:
        super().__init__()
        
    def add_trait(self, trait : FootprintTrait):
        return super().add_trait(trait)

class Interface(FaebrykLibObject):
    def __init__(self) -> None:
        super().__init__()
        self.connections = []

    def add_trait(self, trait: InterfaceTrait) -> None:
        return super().add_trait(trait)

    def connect(self, other: Interface):
        assert(type(other) is type(self))
        self.connections.append(other)

class Component(FaebrykLibObject):
    def __init__(self) -> None:
        super().__init__()

    def add_trait(self, trait: ComponentTrait) -> None:
        return super().add_trait(trait)

    def from_comp(other: Component) -> Component:
        #TODO traits?
        return Component()

class Link(FaebrykLibObject):
    def __init__(self) -> None:
        super().__init__()

    def add_trait(self, trait: LinkTrait) -> None:
        return super().add_trait(trait)

class Parameter(FaebrykLibObject):
    def __init__(self) -> None:
        super().__init__()

    def add_trait(self, trait: ParameterTrait) -> None:
        return super().add_trait(trait)
# -----------------------------------------------------------------------------

# Interface Traits ------------------------------------------------------------
class is_composed(InterfaceTrait):
    def get_components(self) -> list(Interface):
        raise NotImplemented

class can_list_interfaces(InterfaceTrait):
    def get_interfaces(self) -> list(Interface):
        raise NotImplemented

class contructable_from_interface_list(InterfaceTrait):
    def from_interfaces(self, interfaces: Iterable(Interface)):
        raise NotImplemented

# -----------------------------------------------------------------------------

# Component Traits ------------------------------------------------------------
class has_type_description(ComponentTrait):
    def get_type_description(self) -> str:
        raise NotImplemented

class has_defined_type_description(has_type_description):
    def __init__(self, value : str) -> None:
        super().__init__()
        self.value = value

    def get_type_description(self) -> str:
        return self.value

class has_interfaces(ComponentTrait):
    def get_interfaces(self) -> list(Interface):
        raise NotImplemented

class contructable_from_component(ComponentTrait):
    def from_comp(self, comp: Component):
        raise NotImplemented
    
# -----------------------------------------------------------------------------

# Footprint Traits ------------------------------------------------------------
class has_kicad_footprint(FootprintTrait):
    def get_kicad_footprint(self) -> str:
        raise NotImplemented
# -----------------------------------------------------------------------------

# Parameter Traits ------------------------------------------------------------
class is_representable_by_single_value(ParameterTrait):
    def __init__(self, value: typing.Any) -> None:
        super().__init__()
        self.value = value

    def get_single_representing_value(self):
        return self.value
# -----------------------------------------------------------------------------

# Parameter -------------------------------------------------------------------
class Constant(Parameter):
    def __init__(self, value: typing.Any) -> None:
        super().__init__()
        self.value = value
        self.add_trait(is_representable_by_single_value(
            self.value
        ))

# -----------------------------------------------------------------------------

# Footprints ------------------------------------------------------------------
class DIP(Footprint):
    def __init__(self, pin_cnt: int, spacing_mm: int, long_pads: bool) -> None:
        super().__init__()

        class _has_kicad_footprint(FootprintTrait):
            def get_kicad_footprint() -> str:
                return \
                    "DIP-{leads}-W{spacing:.2f}mm{longpads}".format(
                        leads=pin_cnt,
                        spacing=spacing_mm,
                        longpads="_LongPads" if long_pads else ""
                    )

        self.add_trait(_has_kicad_footprint())
# -----------------------------------------------------------------------------

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
    def __init__(self) -> None:
        super().__init__()
        self.hv = Electrical()
        self.lv = Electrical()

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
                return p

        self.add_trait(is_composed([self.hv, self.lv]))


class I2C(Interface):
    def __init__(self) -> None:
        super().__init__()
        self.sda = Electrical()
        self.sdc = Electrical()
        self.gnd = Electrical()
        self.add_trait(is_composed(
            [self.sda, self.sdc, self.gnd]
        ))
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
            for nested in i.get_interfaces()
    ]

# -----------------------------------------------------------------------------

# Components ------------------------------------------------------------------
class Resistor(Component):
    def __init__(self, resistance : Parameter):
        super().__init__()

        self.interfaces = [Electrical(), Electrical()]
        self.resistance = resistance

        class _has_type_description(has_type_description):
            @staticmethod
            def get_description():
                resistance = self.resistance
                assert(type(resistance) is Constant)
                return unit_map(resistance, ["µΩ", "mΩ", "Ω", "KΩ", "MΩ", "GΩ"], start="Ω")
        
        class _has_interfaces(has_interfaces):
            @staticmethod
            def get_interfaces() -> list(Interface):
                return self.interfaces

        class _contructable_from_component(contructable_from_component):
            @staticmethod
            def from_component(comp: Component, resistance: Parameter) -> Resistor:
                assert(comp.has_trait(has_interfaces))
                interfaces = comp.get_trait(has_interfaces).get_interfaces()
                assert(len(interfaces) == 2)
                assert(len([i for i in interfaces if type(i) is not Electrical]) == 0)

                r = Resistor(resistance)
                r.interfaces = interfaces

                return r

        self.add_trait(_has_type_description())
        self.add_trait(_has_interfaces())
        self.add_trait(_contructable_from_component())


class NAND(Component):
    def __init__(self, input_cnt: int):
        super().__init__()

        self.power = Power()
        self.output = Electrical()
        self.inputs = times(input_cnt, Electrical)

        class _has_interfaces(has_interfaces):
            @staticmethod
            def get_interfaces():
                return get_all_interfaces([self.power, self.output, *self.inputs])

        class _constructable_from_component(contructable_from_component):
            @staticmethod
            def from_comp(comp: Component) -> NAND:
                dummy = NAND(2)
                base_cnt = len(get_all_interfaces(dummy))

                assert(comp.has_trait(has_interfaces))
                interfaces = comp.get_trait(has_interfaces).get_interfaces()
                assert(len(interfaces) >= base_cnt)
                assert(len([i for i in interfaces if type(i) is not Electrical]) == 0)

                new_input_cnt = (len(interfaces) - base_cnt)/len(dummy.inputs[0].get_interfaces()) + 2
                n = NAND(new_input_cnt)
                it = iter(interfaces)

                n.power = n.power.from_interfaces(it)
                n.output = n.output.from_interfaces(it)
                n.inputs = [i.from_interfaces(it) for i in n.inputs]
                
                return n

            
        self.add_trait(_has_interfaces())
        self.add_trait(_constructable_from_component)


class CD4011(Component):
    def __init__(self):
        super().__init__()

        self.power = Power()
        self.nands = times(4, lambda: NAND(input_cnt=2))

        nand_inout_interfaces = [i for n in self.nands for i in get_all_interfaces([n.output, *n.inputs])]
        self.in_outs = times(len(nand_inout_interfaces), Electrical)

        self._internal_connect()

        class _has_interfaces(has_interfaces):
            @staticmethod
            def get_interfaces():
                return get_all_interfaces([self.power, *self.nand_ifs])

        class _constructable_from_component(contructable_from_component):
            @staticmethod
            def from_comp(comp: Component) -> CD4011:
                c = CD4011()

                assert(comp.has_trait(has_interfaces))
                interfaces = comp.get_trait(has_interfaces).get_interfaces()
                assert(len(interfaces) == len(c.get_trait(has_interfaces).get_interfaces()))
                assert(len([i for i in interfaces if type(i) is not Electrical]) == 0)

                c.power.hv = interfaces[13]
                c.power.lv = interfaces[6]
                c.in_outs = [interfaces[i] for i in [2,0,1,5,3,4,10,11,12,9,7,8]]

                #TODO we can see a problem here:
                #   when we replace the in_outs we would need to call _internal_connect again
                #   but our nands are already connected to the interfaces of c before replacement
                #   since they hold that reference they also wont get destructed
                #   probably the best way to go about this is to have the "from" method destruct
                #   the old interface manually or so

                #self.nands[0].inputs[0].connect(self.interfaces[0])
                #self.nands[0].inputs[1].connect(self.interfaces[1])
                #self.nands[0].output.connect(self.interfaces[2])

                #self.nands[1].inputs[0].connect(self.interfaces[3])
                #self.nands[1].inputs[1].connect(self.interfaces[4])
                #self.nands[1].output.connect(self.interfaces[5])

                #self.nands[2].inputs[0].connect(self.interfaces[11])
                #self.nands[2].inputs[1].connect(self.interfaces[12])
                #self.nands[2].output.connect(self.interfaces[10])

                #self.nands[3].inputs[0].connect(self.interfaces[7])
                #self.nands[3].inputs[1].connect(self.interfaces[8])
                #self.nands[3].output.connect(self.interfaces[9])
        
        
        self.add_trait(_has_interfaces())
        self.add_trait(_constructable_from_component)
        self.add_trait(has_defined_type_description("cd4011"))


    def _internal_connect(self):
        it = iter(self.in_outs)
        for n in self.nands:
            n.power.connect(self.power)
            n.output.connect(next(it))

            for i in n.inputs:
                i.connect(next(it))

        assert(len(self.interfaces) == 14)




        
# -----------------------------------------------------------------------------
