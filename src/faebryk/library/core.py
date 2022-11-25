# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

from __future__ import annotations

import logging
from abc import ABC
from typing import List, Optional, Type, TypeVar

from typing_extensions import Self

from faebryk.libs.util import Holder

logger = logging.getLogger("library")

# 1st order classes -----------------------------------------------------------
class Trait:
    @classmethod
    def impl(cls: Type[Trait]):
        class _Impl(TraitImpl, cls):
            pass

        return _Impl


class TraitImpl(ABC):
    trait: Type[Trait]

    def __init__(self) -> None:
        self._obj = None

        found = False
        bases = type(self).__bases__
        while not found:
            for base in bases:
                if not issubclass(base, TraitImpl) and issubclass(base, Trait):
                    self.trait = base
                    found = True
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

    # override this to implement a dynamic trait
    def is_implemented(self):
        return True


class FaebrykLibObject:
    traits: List[TraitImpl]

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
        # TODO deal with dynamic traits
        for i, t in enumerate(self.traits):
            hit, replace = t.cmp(trait)
            if hit:
                if replace == trait:
                    t.remove_obj()
                    self.traits[i] = replace
                return

        # No hit: Add new trait
        self.traits.append(trait)

    def _find(self, trait, only_implemented: bool):
        return list(
            filter(
                lambda tup: tup[1].implements(trait)
                and (tup[1].is_implemented() or not only_implemented),
                enumerate(self.traits),
            )
        )

    def del_trait(self, trait):
        candidates = self._find(trait, only_implemented=False)
        assert len(candidates) <= 1
        if len(candidates) == 0:
            return
        assert len(candidates) == 1, "{} not in {}[{}]".format(trait, type(self), self)
        i, impl = candidates[0]
        assert self.traits[i] == impl
        impl.remove_obj()
        del self.traits[i]

    def has_trait(self, trait) -> bool:
        return len(self._find(trait, only_implemented=True)) > 0

    T = TypeVar("T", bound=Trait)

    def get_trait(self, trait: Type[T]) -> T:
        candidates = self._find(trait, only_implemented=True)
        assert len(candidates) <= 1
        assert len(candidates) == 1, "{} not in {}[{}]".format(trait, type(self), self)

        out = candidates[0][1]
        assert isinstance(out, trait)
        return out


# -----------------------------------------------------------------------------

# Traits ----------------------------------------------------------------------
class InterfaceTrait(Trait):
    pass


class NodeTrait(Trait):
    pass


class LinkTrait(Trait):
    pass


class ParameterTrait(Trait):
    pass


# -----------------------------------------------------------------------------


# FaebrykLibObjects -----------------------------------------------------------
class Link(FaebrykLibObject):
    def __init__(self) -> None:
        super().__init__()

    def add_trait(self, trait: TraitImpl) -> None:
        assert isinstance(trait, LinkTrait)
        return super().add_trait(trait)

    def get_connections(self) -> List[Interface]:
        raise NotImplementedError


class Interface(FaebrykLibObject):
    connections: List[Link]
    component: Optional[Node]

    def __init__(self) -> None:
        super().__init__()
        self.connections = []
        # can't put it into constructor
        # else it needs a reference when defining IFs
        self.component = None

    def add_trait(self, trait: TraitImpl) -> None:
        assert isinstance(trait, InterfaceTrait)
        return super().add_trait(trait)

    # TODO make link trait to initialize from list
    def connect(self, other: Self, linkcls=None) -> Self:
        assert self.component is not None

        from faebryk.library.library.links import LinkDirect

        if linkcls is None:
            linkcls = LinkDirect
        link = linkcls([other, self])
        self.connections.append(link)
        other.connections.append(link)

        return self


# TODO rename to module/node?
class Node(FaebrykLibObject):
    @staticmethod
    def InterfacesCls():
        class InterfaceHolder(Holder(Interface, Node)):
            def handle_add(self, name: str, obj: Interface) -> None:
                assert isinstance(obj, Interface)
                parent: Node = self.get_parent()
                obj.component = parent
                return super().handle_add(name, obj)

            def __init__(self, parent: Node) -> None:
                super().__init__(parent)

                # Default Component Interfaces
                self.children = Interface()
                self.parent = Interface()
                # TODO
                self.external_children = Interface()

        return InterfaceHolder

    @staticmethod
    def NodesCls():
        class NodeHolder(Holder(Node, Node)):
            def handle_add(self, name: str, obj: Node) -> None:
                assert isinstance(obj, Node)
                parent: Node = self.get_parent()
                obj.LLIFs.parent.connect(parent.LLIFs.children)
                return super().handle_add(name, obj)

            def __init__(self, parent: Node) -> None:
                super().__init__(parent)

        return NodeHolder

    class LLIFS(InterfacesCls()):
        pass

    class NODES(NodesCls()):
        pass

    def __init__(self) -> None:
        super().__init__()

        self.LLIFs = Node.LLIFS(self)
        self.NODEs = Node.NODES(self)

    def add_trait(self, trait: TraitImpl) -> None:
        assert isinstance(trait, NodeTrait)
        return super().add_trait(trait)


class Parameter(FaebrykLibObject):
    def __init__(self) -> None:
        super().__init__()

    def add_trait(self, trait: TraitImpl) -> None:
        assert isinstance(trait, ParameterTrait)
        return super().add_trait(trait)


# -----------------------------------------------------------------------------
