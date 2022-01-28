# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

from faebryk.library.core import *
from faebryk.libs.exceptions import FaebrykException
from typing import Iterable

import logging
logger = logging.getLogger("library")

# Interface Traits ------------------------------------------------------------
#class is_composed(InterfaceTrait):
#    def get_components(self) -> list(Interface):
#        raise NotImplemented

class can_list_interfaces(InterfaceTrait):
    def get_interfaces(self) -> list[Interface]:
        raise NotImplementedError()

class contructable_from_interface_list(InterfaceTrait):
    def from_interfaces(self, interfaces: Iterable[Interface]):
        raise NotImplementedError()

class is_part_of_component(InterfaceTrait):
    def get_component(self) -> Component:
        raise NotImplementedError

# -----------------------------------------------------------------------------

# Component Traits ------------------------------------------------------------
class has_type_description(ComponentTrait):
    def get_type_description(self) -> str:
        raise NotImplementedError(type(self))

class has_defined_type_description(has_type_description):
    def __init__(self, value : str) -> None:
        super().__init__()
        self.value = value

    def get_type_description(self) -> str:
        return self.value

class has_interfaces(ComponentTrait):
    def get_interfaces(self) -> list[Interface]:
        raise NotImplementedError()

    def set_interface_comp(self, comp):
        for i in self.get_interfaces():
            i.set_component(comp)

class has_interfaces_list(has_interfaces):
    def __init__(self, comp: Component) -> None:
        super().__init__()
        self.comp = comp

    def get_interfaces(self) -> list[Interface]:
        return self.comp.interfaces

    def set_interface_comp(self, comp=None):
        assert (comp is None or comp == self.comp) 
        super().set_interface_comp(self.comp)

class contructable_from_component(ComponentTrait):
    def from_comp(self, comp: Component):
        raise NotImplementedError()
    
class has_footprint(ComponentTrait):
    def get_footprint(self) -> Footprint:
        raise NotImplementedError()

class has_defined_footprint(has_footprint):
    def __init__(self, fp: Footprint) -> None:
        super().__init__()
        self.fp = fp
    
    def get_footprint(self) -> Footprint:
        return self.fp

class has_footprint_pinmap(ComponentTrait):
    def get_pin_map(self):
        raise NotImplementedError()

class has_defined_footprint_pinmap(has_footprint_pinmap):
    def __init__(self, pin_map) -> None:
        super().__init__()
        self.pin_map = pin_map

    def get_pin_map(self):
        return self.pin_map

# -----------------------------------------------------------------------------

# Footprint Traits ------------------------------------------------------------
class has_kicad_footprint(FootprintTrait):
    def get_kicad_footprint(self) -> str:
        raise NotImplementedError()
    
class has_kicad_manual_footprint(has_kicad_footprint):
    def __init__(self, str) -> None:
        super().__init__()
        self.str = str

    def get_kicad_footprint(self):
        return self.str
    
# -----------------------------------------------------------------------------

# Parameter Traits ------------------------------------------------------------
class is_representable_by_single_value(ParameterTrait):
    def __init__(self, value: typing.Any) -> None:
        super().__init__()
        self.value = value

    def get_single_representing_value(self):
        return self.value
# -----------------------------------------------------------------------------