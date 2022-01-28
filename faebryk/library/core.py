# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

from __future__ import annotations
from faebryk.libs.exceptions import FaebrykException
import typing

import logging
logger = logging.getLogger("library")

# 1st order classes -----------------------------------------------------------
class Trait:
    def __eq__(self, other: Trait) -> bool:
        return isinstance(self, other)

class FaebrykLibObject:
    def __new__(cls, *args, **kwargs):
        self = super().__new__(cls)
        #TODO maybe dict[class => [obj]
        self.traits = []
        return self

    def __init__(self) -> None:
        pass

    def add_trait(self, trait : Trait) -> None:
        if type(trait) not in self.traits:
            self.traits.append(trait)
            return

        self.traits[self.traits.index(type(trait))] = trait

    def has_trait(self, trait) -> bool:
        #return any(lambda t: type(t) is trait, self.traits)
        return trait in self.traits

    def get_trait(self, trait):
        assert (trait in self.traits), "{} not in {}[{}]".format(trait, type(self), self)
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
    def __new__(cls, *args, **kwargs):
        self = super().__new__(cls)
        self.connections = []
        return self

    def __init__(self) -> None:
        super().__init__()

    def add_trait(self, trait: InterfaceTrait) -> None:
        return super().add_trait(trait)

    def connect(self, other: Interface):
        assert (type(other) is type(self)), "{} is not {}".format(type(other), type(self))
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