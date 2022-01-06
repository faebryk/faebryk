# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

from typing import Iterable
from faebryk.libs.exceptions import FaebrykException
import typing

import logging
logger = logging.getLogger("library")

# 1st order classes -----------------------------------------------------------
class Trait:
    def __init__(self) -> None:
        pass

class FaebrykLibObject:
    def __init__(self) -> None:
        #TODO maybe dict[class => [obj]
        self.traits = []

    def add_trait(self, trait : Trait) -> None:
        self.traits.append(trait)
# -----------------------------------------------------------------------------

# Traits ----------------------------------------------------------------------
class FootprintTrait(Trait):
    def __init__(self) -> None:
        super().__init__()

class InterfaceTrait(Trait):
    def __init__(self) -> None:
        super().__init__()

class ComponentTrait(Trait):
    def __init__(self) -> None:
        super().__init__()

class LinkTrait(Trait):
    def __init__(self) -> None:
        super().__init__()

class ParameterTrait(Trait):
    def __init__(self) -> None:
        super().__init__()
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
        self.connections.append(other)

class Component(FaebrykLibObject):
    def __init__(self, interfaces : list(Interface) = None) -> None:
        super().__init__()
        if interfaces is None:
            interfaces = []
        self.interfaces = interfaces

    def add_trait(self, trait: ComponentTrait) -> None:
        return super().add_trait(trait)

    def from_comp(other: Component) -> Component:
        return Component(interfaces=other.interfaces)

    #TODO replace_by?


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
    def __init__(self, interfaces : Iterable(Interface)) -> None:
        super().__init__()
        self.interfaces = list(interfaces)

# -----------------------------------------------------------------------------

# Component Traits ------------------------------------------------------------
class has_type_description(ComponentTrait):
    def __init__(self) -> None:
        super().__init__()

    def get_type_description(self) -> str:
        pass

class has_defined_type_description(has_type_description):
    def __init__(self, value : str) -> None:
        super().__init__()
        self.value = value

    def get_type_description(self) -> str:
        return self.value
# -----------------------------------------------------------------------------

# Footprint Traits ------------------------------------------------------------
class has_kicad_footprint(FootprintTrait):
    def __init__(self, identifier : str) -> None:
        super().__init__()
        self.identifier = identifier

    def get_kicad_footprint(self):
        return self.identifier
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

        self.add_trait(has_kicad_footprint(
            "DIP-{leads}-W{spacing:.2f}mm{longpads}".format(
                leads=pin_cnt,
                spacing=spacing_mm,
                longpads="_LongPads" if long_pads else ""
            )
        ))
# -----------------------------------------------------------------------------

# Interfaces ------------------------------------------------------------------
class Electrical(Interface):
    def __init__(self) -> None:
        super().__init__()

class Bus(Interface):
    def __init__(self, interfaces: Iterable(Electrical)) -> None:
        super().__init__()
        self.add_trait(is_composed(interfaces))

class Power(Interface):
    def __init__(self) -> None:
        super().__init__()
        self.hv = Electrical()
        self.lv = Electrical()
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

# -----------------------------------------------------------------------------

# Components ------------------------------------------------------------------
class Resistor(Component):
    def from_comp(comp : Component, resistance : Parameter) -> Resistor:
        return Resistor(resistance, comp.interfaces)

    def __init__(self, resistance : Parameter, interfaces : list(Interface) = None):
        super().__init__(intefaces=default_with(interfaces, [Electrical(), Electrical()]))
        self.resistance = resistance

        class resistor_type_description(has_type_description):
            def __init__(self, parent : Resistor) -> None:
                super().__init__()
                self.parent = parent

            def get_description():
                return "{}R".format(self.parent.resistance)
        
        self.add_trait(resistor_type_description(self))

class NAND(Component):
    def __init__(self, input_cnt: int, interfaces : list(Interface) = None):

        super().__init__(intefaces=default_with(interfaces, 
            *times(2, Electrical), #power
            Electrical(), #output
            *times(input_cnt, Electrical) #inputs
        ))

        self.inputs = self.interfaces[2:-1]
        self.output = self.interfaces[2]
        self.power = Power() #TODO damn this sucks, now power cant get the interfaces anymore


class CD4011(Component):
    def __init__(self, interfaces : list(Interface) = None):
        super().__init__(interfaces=default_with(interfaces, 
            times(14, Electrical)
        ))

        self.nands = times(4, lambda: NAND(input_cnt=2))
        self.add_trait(has_defined_type_description("cd4011"))
        self.power = Power()

        for n in self.nands:
            n.power.connect(self.power)

        self.nands[0].inputs[0].connect(self.interfaces[1])
        self.nands[0].inputs[1].connect(self.interfaces[2])
        self.nands[0].inputs.connect(self.interfaces[3])

        self.nands[1].inputs[0].connect(self.interfaces[4])
        self.nands[1].inputs[1].connect(self.interfaces[5])
        self.nands[1].output.connect(self.interfaces[6])

        self.nands[2].inputs[0].connect(self.interfaces[12])
        self.nands[2].inputs[1].connect(self.interfaces[13])
        self.nands[2].output.connect(self.interfaces[11])

        self.nands[3].inputs[0].connect(self.interfaces[8])
        self.nands[3].inputs[1].connect(self.interfaces[9])
        self.nands[3].output.connect(self.interfaces[10])
# -----------------------------------------------------------------------------
