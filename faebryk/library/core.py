# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

from __future__ import annotations
from faebryk.libs.exceptions import FaebrykException
from typing import Iterable, List

import logging

from faebryk.libs.util import Holder

logger = logging.getLogger("library")

# 1st order classes -----------------------------------------------------------
class Trait:
    @classmethod
    def impl(cls):
        class _Impl(TraitImpl, cls):
            pass

        return _Impl


class TraitImpl:
    def __init__(self) -> None:
        self._obj = None

        self.trait = None
        bases = type(self).__bases__
        while not self.trait:
            for base in bases:
                if not issubclass(base, TraitImpl) and issubclass(base, Trait):
                    self.trait = base
                    break
            bases = [
                new_base
                for base in bases
                if issubclass(base, TraitImpl)
                for new_base in base.__bases__
            ]
            assert len(bases) > 0

        assert type(self.trait) is type
        assert issubclass(self.trait, Trait)
        assert self.trait is not TraitImpl

    def set_obj(self, _obj):
        self._obj = _obj

    def remove_obj(self):
        self._obj = None

    def get_obj(self):
        assert self._obj is not None, "trait is not linked to object"
        return self._obj

    def cmp(self, other: TraitImpl) -> tuple[bool, TraitImpl]:
        assert type(other), TraitImpl

        # If other same or more specific
        if other.implements(self.trait):
            return True, other

        # If we are more specific
        if self.implements(other.trait):
            return True, self

        return False, self

    def implements(self, trait: type):
        assert issubclass(trait, Trait)

        return issubclass(self.trait, trait)


class FaebrykLibObject:
    def __new__(cls, *args, **kwargs):
        self = super().__new__(cls)
        # TODO maybe dict[class => [obj]
        self.traits = []
        return self

    def __init__(self) -> None:
        pass

    def add_trait(self, trait: TraitImpl) -> None:
        assert isinstance(trait, TraitImpl), ("not a traitimpl:", trait)
        assert isinstance(trait, Trait)
        assert trait._obj is None, "trait already in use"
        trait.set_obj(self)

        # Override existing trait if more specific or same
        for i, t in enumerate(self.traits):
            hit, replace = t.cmp(trait)
            if hit:
                if replace == trait:
                    t.remove_obj()
                    self.traits[i] = replace
                return

        # No hit: Add new trait
        self.traits.append(trait)

    def _find(self, trait):
        return list(
            filter(lambda tup: tup[1].implements(trait), enumerate(self.traits))
        )

    def del_trait(self, trait):
        candidates = self._find(trait)
        assert len(candidates) <= 1
        if len(candidates) == 0:
            return
        assert len(candidates) == 1, "{} not in {}[{}]".format(trait, type(self), self)
        i, impl = candidates[0]
        assert self.traits[i] == impl
        impl.remove_obj()
        del self.traits[i]

    def has_trait(self, trait) -> bool:
        return len(self._find(trait)) > 0

    def get_trait(self, trait):
        candidates = self._find(trait)
        assert len(candidates) <= 1
        assert len(candidates) == 1, "{} not in {}[{}]".format(trait, type(self), self)

        return candidates[0][1]


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

    def add_trait(self, trait: FootprintTrait):
        return super().add_trait(trait)


class Interface(FaebrykLibObject):
    from faebryk.libs.util import NotifiesOnPropertyChange

    @classmethod
    def InterfacesCls(cls):
        class _Interfaces(Holder(Interface)):
            def __init__(self, intf: Interface) -> None:
                self.unnamed = []
                self._intf = intf

                super().__init__()

            def handle_add(self, intf: Interface):
                if self._intf.component is None:
                    return
                intf.set_component(self._intf.component)

            # TODO this is not working anymore
            # due to not putting into the list
            # maybe just remove the whole thing
            def add(self, intf: Interface):
                self.unnamed += (intf,)
                if self._intf.component is None:
                    return
                intf.set_component(self._intf.component)

            def add_all(self, intfs: Iterable[Interface]):
                for intf in intfs:
                    self.add(intf)

        return _Interfaces

    def __new__(cls, *args, component=None, **kwargs):
        self = super().__new__(cls)
        self.connections = []
        self.component = None
        if component is not None:
            self.set_component(component)
        return self

    def __init__(self) -> None:
        super().__init__()

        self.IFs = Interface.InterfacesCls()(self)

    def add_trait(self, trait: InterfaceTrait) -> None:
        return super().add_trait(trait)

    def connect(self, other: Interface) -> Interface:
        assert type(other) is type(self), "{} is not {}".format(type(other), type(self))
        self.connections.append(other)
        other.connections.append(self)

        return self

    def connect_all(self, others: list[Interface]) -> Interface:
        for i in others:
            self.connect(i)

        return self

    def connect_via(self, bridge: Component, target: Interface):
        from faebryk.library.traits.component import can_bridge

        bridge.get_trait(can_bridge).bridge(self, target)

    def connect_via_chain(self, bridges: list[Interface], target: Interface):
        from faebryk.library.traits.component import can_bridge

        end = self
        for bridge in bridges:
            end.connect(bridge.get_trait(can_bridge).get_in())
            end = bridge.get_trait(can_bridge).get_out()
        end.connect(target)

    def set_component(self, component):
        from faebryk.library.traits.interface import is_part_of_component

        self.component = component

        class _(is_part_of_component.impl()):
            @staticmethod
            def get_component() -> Component:
                return self.component

        if component is None:
            self.del_trait(is_part_of_component)
        else:
            self.add_trait(_())

        # TODO I think its nicer to have a parent relationship to the other interface
        #   instead of carrying the component through all compositions
        for i in self.IFs.get_all():
            assert i != self
            i.set_component(component)


class Component(FaebrykLibObject):
    from faebryk.libs.util import NotifiesOnPropertyChange

    @classmethod
    def InterfacesCls(cls):
        class _Interfaces(Holder(Interface)):
            def __init__(self, comp: Component) -> None:
                self._comp = comp
                self.unnamed = ()

                # helper array for next method
                self._unpopped = []

                super().__init__()

            def handle_add(self, intf: Interface):
                intf.set_component(self._comp)

            def add(self, intf: Interface):
                self.unnamed += (intf,)
                intf.set_component(self._comp)
                self._unpopped.append(intf)

            def add_all(self, intfs: Iterable[Interface]):
                for intf in intfs:
                    self.add(intf)

            """ returns iterator on unnamed interfaces """

            def next(self):
                assert len(self._unpopped) > 0, "No more interfaces to pop"
                return self._unpopped.pop(0)

        return _Interfaces

    @classmethod
    def ComponentsCls(cls):
        class _Components(Holder(Component)):
            def __init__(self, comp: Component) -> None:
                self._comp = comp
                self.unnamed = ()

                super().__init__()

            def add(self, cmp: Component):
                self.unnamed += (cmp,)

            def add_all(self, cmps: Iterable[Component]):
                for cmp in cmps:
                    self.add(cmp)

        return _Components

    def __init__(self) -> None:
        super().__init__()

        self.IFs = Component.InterfacesCls()(self)
        self.CMPs = Component.ComponentsCls()(self)

    def add_trait(self, trait: ComponentTrait) -> None:
        return super().add_trait(trait)

    @staticmethod
    def from_comp(other: Component) -> Component:
        # TODO traits?
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
