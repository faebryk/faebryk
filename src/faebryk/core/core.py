# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

from __future__ import annotations

import inspect
import logging
from abc import ABC, abstractmethod
from typing import Callable, Generic, Iterable, Optional, Sequence, Type, TypeVar

from faebryk.libs.util import Holder, NotNone, cast_assert
from typing_extensions import Self

logger = logging.getLogger(__name__)

# Saves stack trace for each link for debugging
# Can be enabled from test cases and apps, but very slow, so only for debug
LINK_TB = False

# 1st order classes -----------------------------------------------------------
T = TypeVar("T", bound="FaebrykLibObject")


class Trait(Generic[T]):
    @classmethod
    def impl(cls: Type[Trait]):
        T_ = TypeVar("T_", bound="FaebrykLibObject")

        class _Impl(Generic[T_], TraitImpl[T_], cls):
            ...

        return _Impl[T]


U = TypeVar("U", bound="FaebrykLibObject")


class TraitImpl(Generic[U], ABC):
    trait: Type[Trait[U]]

    def __init__(self) -> None:
        super().__init__()

        self._obj: U | None = None

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

    def set_obj(self, _obj: U):
        self._obj = _obj
        self.on_obj_set()

    def on_obj_set(self):
        ...

    def remove_obj(self):
        self._obj = None

    def get_obj(self) -> U:
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
    traits: list[TraitImpl]

    def __new__(cls, *args, **kwargs):
        self = super().__new__(cls)
        # TODO maybe dict[class => [obj]
        self.traits = []
        return self

    def __init__(self) -> None:
        ...

    _TImpl = TypeVar("_TImpl", bound=TraitImpl)

    # TODO type checking InterfaceTrait -> Interface
    def add_trait(self, trait: _TImpl) -> _TImpl:
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
                return replace

        # No hit: Add new trait
        self.traits.append(trait)
        return trait

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

    V = TypeVar("V", bound=Trait)

    def get_trait(self, trait: Type[V]) -> V:
        assert not issubclass(
            trait, TraitImpl
        ), "You need to specify the trait, not an impl"

        candidates = self._find(trait, only_implemented=True)
        assert len(candidates) <= 1
        assert len(candidates) == 1, "{} not in {}[{}]".format(trait, type(self), self)

        out = candidates[0][1]
        assert isinstance(out, trait)
        return out


# -----------------------------------------------------------------------------

# Traits ----------------------------------------------------------------------
TI = TypeVar("TI", bound="GraphInterface")


class _InterfaceTrait(Generic[TI], Trait[TI]):
    ...


class InterfaceTrait(_InterfaceTrait["GraphInterface"]):
    ...


TN = TypeVar("TN", bound="Node")


class _NodeTrait(Generic[TN], Trait[TN]):
    ...


class NodeTrait(_NodeTrait["Node"]):
    ...


TL = TypeVar("TL", bound="Link")


class _LinkTrait(Generic[TL], Trait[TL]):
    ...


class LinkTrait(_LinkTrait["Link"]):
    ...


TP = TypeVar("TP", bound="Parameter")


class _ParameterTrait(Generic[TP], Trait[TP]):
    ...


class ParameterTrait(_ParameterTrait["Parameter"]):
    ...


class can_determine_partner_by_single_end(LinkTrait):
    @abstractmethod
    def get_partner(self, other: GraphInterface) -> GraphInterface:
        ...


# -----------------------------------------------------------------------------


# FaebrykLibObjects -----------------------------------------------------------
class Link(FaebrykLibObject):
    def __init__(self) -> None:
        super().__init__()

        if LINK_TB:
            self.tb = inspect.stack()

    def get_connections(self) -> list[GraphInterface]:
        raise NotImplementedError

    def __eq__(self, __value: Link) -> bool:
        return set(self.get_connections()) == set(__value.get_connections())

    def __hash__(self) -> int:
        return super().__hash__()

    def __str__(self) -> str:
        return (
            f"{type(self).__name__}"
            f"([{', '.join(str(i) for i in self.get_connections())}])"
        )


class LinkSibling(Link):
    def __init__(self, interfaces: list[GraphInterface]) -> None:
        super().__init__()
        self.interfaces = interfaces

    def get_connections(self) -> list[GraphInterface]:
        return self.interfaces


class LinkParent(Link):
    def __init__(self, name: str, interfaces: list[GraphInterface]) -> None:
        super().__init__()
        self.name = name

        assert all([isinstance(i, GraphInterfaceHierarchical) for i in interfaces])
        # TODO rethink invariant
        assert len(interfaces) == 2
        assert len([i for i in interfaces if i.is_parent]) == 1  # type: ignore

        self.interfaces: list[GraphInterfaceHierarchical] = interfaces  # type: ignore

    @classmethod
    def curry(cls, name: str):
        def curried(interfaces: list[GraphInterface]):
            return LinkParent(name, interfaces)

        return curried

    def get_connections(self):
        return self.interfaces

    def get_parent(self):
        return [i for i in self.interfaces if i.is_parent][0]

    def get_child(self):
        return [i for i in self.interfaces if not i.is_parent][0]


class LinkDirect(Link):
    def __init__(self, interfaces: list[GraphInterface]) -> None:
        super().__init__()
        assert len(set(map(type, interfaces))) == 1
        self.interfaces = interfaces

        if len(interfaces) == 2:

            class _(can_determine_partner_by_single_end.impl()):
                def get_partner(_self, other: GraphInterface):
                    return [i for i in self.interfaces if i is not other][0]

            self.add_trait(_())

    def get_connections(self) -> list[GraphInterface]:
        return self.interfaces


class LinkFilteredException(Exception):
    ...


class _TLinkDirectShallow(LinkDirect):
    def __new__(cls, *args, **kwargs):
        if cls is _TLinkDirectShallow:
            raise TypeError(
                "Can't instantiate abstract class _TLinkDirectShallow directly"
            )
        return LinkDirect.__new__(cls, *args, **kwargs)


def LinkDirectShallow(if_filter: Callable[[LinkDirect, GraphInterface], bool]):
    class _LinkDirectShallow(_TLinkDirectShallow):
        i_filter = if_filter

        def __init__(self, interfaces: list[GraphInterface]) -> None:
            if not all(map(self.i_filter, interfaces)):
                raise LinkFilteredException()
            super().__init__(interfaces)

    return _LinkDirectShallow


class GraphInterface(FaebrykLibObject):
    def __init__(self) -> None:
        super().__init__()
        self.connections: list[Link] = []
        # can't put it into constructor
        # else it needs a reference when defining IFs
        self._node: Optional[Node] = None
        self.name: str = type(self).__name__

        self.cache: dict[GraphInterface, Link] = {}

    @property
    def node(self):
        return NotNone(self._node)

    @node.setter
    def node(self, value: Node):
        self._node = value

    # TODO make link trait to initialize from list
    def connect(self, other: Self, linkcls=None) -> Self:
        assert self.node is not None
        assert other is not self

        if linkcls is None:
            linkcls = LinkDirect
        link = linkcls([other, self])

        assert link not in self.connections
        assert link not in other.connections
        self.connections.append(link)
        other.connections.append(link)
        try:
            logger.debug(f"GIF connection: {link}")
        # TODO
        except Exception:
            ...

        self.cache[other] = link
        return self

    def get_direct_connections(self) -> set[GraphInterface]:
        return set(self.cache.keys())

    def _is_connected(self, other: GraphInterface):
        return self.cache.get(other)

    def is_connected(self, other: GraphInterface):
        return self._is_connected(other) or other._is_connected(self)

    def get_full_name(self):
        return f"{self.node.get_full_name()}.{self.name}"

    def __str__(self) -> str:
        return f"{str(self.node)}.{self.name}"

    def __repr__(self) -> str:
        return (
            super().__repr__() + f"| {self.get_full_name()}"
            if self._node is not None
            else "| <No None>"
        )


class GraphInterfaceHierarchical(GraphInterface):
    def __init__(self, is_parent: bool) -> None:
        super().__init__()
        self.is_parent = is_parent

    # TODO make consistent api with get_parent
    def get_children(self) -> list[tuple[str, Node]]:
        assert self.is_parent

        hier_conns = [c for c in self.connections if isinstance(c, LinkParent)]
        if len(hier_conns) == 0:
            return []

        return [(c.name, c.get_child().node) for c in hier_conns]

    def get_parent(self) -> tuple[Node, str] | None:
        assert not self.is_parent

        hier_conns = [c for c in self.connections if isinstance(c, LinkParent)]
        if len(hier_conns) == 0:
            return None
        # TODO reconsider this invariant
        assert len(hier_conns) == 1

        conn = hier_conns[0]
        assert isinstance(conn, LinkParent)
        parent = conn.get_parent()

        return parent.node, conn.name


class GraphInterfaceSelf(GraphInterface):
    ...


class GraphInterfaceModuleSibling(GraphInterface):
    ...


class GraphInterfaceModuleConnection(GraphInterface):
    ...


class Node(FaebrykLibObject):
    @classmethod
    def GraphInterfacesCls(cls):
        class InterfaceHolder(Holder(GraphInterface, cls)):
            def handle_add(self, name: str, obj: GraphInterface) -> None:
                assert isinstance(obj, GraphInterface)
                parent: Node = self.get_parent()
                obj.node = parent
                obj.name = name
                if not isinstance(obj, GraphInterfaceSelf):
                    if hasattr(self, "self"):
                        obj.connect(self.self, linkcls=LinkSibling)
                if isinstance(obj, GraphInterfaceSelf):
                    assert obj is self.self
                    for target in self.get_all():
                        if target is self.self:
                            continue
                        target.connect(obj, linkcls=LinkSibling)
                return super().handle_add(name, obj)

            def __init__(self, parent: Node) -> None:
                super().__init__(parent)

                # Default Component Interfaces
                self.self = GraphInterfaceSelf()
                self.children = GraphInterfaceHierarchical(is_parent=True)
                self.parent = GraphInterfaceHierarchical(is_parent=False)

        return InterfaceHolder

    NT = TypeVar("NT", bound="Node")

    @classmethod
    def NodesCls(cls, t: Type[NT]):
        class NodeHolder(Holder(t, cls)):
            def handle_add(self, name: str, obj: Node.NT) -> None:
                assert isinstance(obj, t)
                parent: Node = self.get_parent()
                obj.GIFs.parent.connect(parent.GIFs.children, LinkParent.curry(name))
                return super().handle_add(name, obj)

            def __init__(self, parent: Node) -> None:
                super().__init__(parent)

        return NodeHolder

    @classmethod
    def GIFS(cls):
        return cls.GraphInterfacesCls()

    @classmethod
    def NODES(cls):
        return cls.NodesCls(Node)

    def __init__(self) -> None:
        super().__init__()

        self.GIFs = Node.GIFS()(self)
        self.NODEs = Node.NODES()(self)

    def get_graph(self):
        from faebryk.core.graph import Graph

        return Graph([self])

    def get_parent(self):
        return self.GIFs.parent.get_parent()

    def get_hierarchy(self) -> list[tuple[Node, str]]:
        parent = self.get_parent()
        if not parent:
            return [(self, "*")]
        parent_obj, name = parent

        return parent_obj.get_hierarchy() + [(self, name)]

    def get_full_name(self, types: bool = False):
        hierarchy = self.get_hierarchy()
        if types:
            return ".".join([f"{name}|{type(obj).__name__}" for obj, name in hierarchy])
        else:
            return ".".join([f"{name}" for _, name in hierarchy])

    def __str__(self) -> str:
        return f"<{self.get_full_name(types=True)}>"

    def __repr__(self) -> str:
        return f"{str(self)}(@{hex(id(self))})"


class Parameter(FaebrykLibObject):
    class ResolutionException(Exception):
        ...

    def __init__(self) -> None:
        super().__init__()

    # TODO replace with better (graph-based resolution)
    def resolve(self, other: "Parameter") -> "Parameter":
        from faebryk.library.TBD import TBD
        from faebryk.library.Constant import Constant
        from faebryk.library.Range import Range

        if isinstance(self, TBD):
            return other
        if isinstance(other, TBD):
            return self

        T = TypeVar("T", bound=Parameter)
        U = TypeVar("U", bound=Parameter)

        def _is_pair(type1: T, type2: U) -> Optional[tuple[T, U]]:
            if isinstance(self, type1) and isinstance(other, type2):
                return self, other
            if isinstance(other, type1) and isinstance(self, type2):
                return other, self
            return None

        if pair := _is_pair(Constant, Constant):
            if len({p.value for p in pair}) != 1:
                raise Parameter.ResolutionException("conflicting constants")
            return pair[0]

        if pair := _is_pair(Constant, Range):
            if not pair[1].contains(pair[0].value):
                raise Parameter.ResolutionException("constant not in range")
            return pair[0]

        if pair := _is_pair(Range, Range):
            min_ = min(p.min for p in pair)
            max_ = max(p.max for p in pair)
            if any(any(not p.contains(v) for p in pair) for v in (min_, max_)):
                raise Parameter.ResolutionException("conflicting ranges")
            return Range(min_, max_)

        raise NotImplementedError

    @staticmethod
    def resolve_all(params: "Sequence[Parameter]"):
        from faebryk.library.TBD import TBD

        params_set = set(params)
        if not params_set:
            return TBD()
        it = iter(params_set)
        most_specific = next(it)
        for param in it:
            most_specific = most_specific.resolve(param)

        return most_specific


# -----------------------------------------------------------------------------

# TODO: move file--------------------------------------------------------------
TMI = TypeVar("TMI", bound="ModuleInterface")


def _resolve_link(links: Iterable[type[Link]]) -> type[Link]:
    from faebryk.core.util import is_type_set_subclasses

    uniq = set(links)
    if len(uniq) == 1:
        return next(iter(uniq))

    if is_type_set_subclasses(uniq, {LinkDirect, _TLinkDirectShallow}):
        return [u for u in uniq if issubclass(u, _TLinkDirectShallow)][0]

    raise NotImplementedError()


class _ModuleInterfaceTrait(Generic[TMI], Trait[TMI]):
    ...


class ModuleInterfaceTrait(_ModuleInterfaceTrait["ModuleInterface"]):
    ...


class _LEVEL:
    """connect depth counter to debug connections in ModuleInterface"""

    def __init__(self) -> None:
        self.value = 0

    def inc(self):
        self.value += 1
        return self.value - 1

    def dec(self):
        self.value -= 1


_CONNECT_DEPTH = _LEVEL()


class ModuleInterface(Node):
    @classmethod
    def NODES(cls):
        class NODES(Node.NODES()):
            ...

        return NODES

    @classmethod
    def GIFS(cls):
        class GIFS(Node.GIFS()):
            sibling = GraphInterfaceModuleSibling()
            connected = GraphInterfaceModuleConnection()

        return GIFS

    def __init__(self) -> None:
        super().__init__()
        self.GIFs = ModuleInterface.GIFS()(self)

    def _connect_siblings_and_connections(
        self, other: ModuleInterface, linkcls: type[Link]
    ) -> ModuleInterface:
        from faebryk.core.util import get_connected_mifs_with_link

        if other is self:
            return self

        # Already connected
        if self.is_connected_to(other):
            return self

        logger.debug(f"MIF connection: {self} to {other}")

        def cross_connect(
            s_group: dict[ModuleInterface, type[Link]],
            d_group: dict[ModuleInterface, type[Link]],
            hint=None,
        ):
            if logger.isEnabledFor(logging.DEBUG) and hint is not None:
                logger.debug(f"Connect {hint} {s_group} -> {d_group}")

            for s, slink in s_group.items():
                for d, dlink in d_group.items():
                    # can happen while connection trees are resolving
                    if s is d:
                        continue
                    link = _resolve_link([slink, dlink, linkcls])

                    s._connect_across_hierarchies(d, linkcls=link)

        def _get_connected_mifs(gif: GraphInterface):
            return {k: type(v) for k, v in get_connected_mifs_with_link(gif).items()}

        # Connect to all connections
        s_con = _get_connected_mifs(self.GIFs.connected) | {self: linkcls}
        d_con = _get_connected_mifs(other.GIFs.connected) | {other: linkcls}
        cross_connect(s_con, d_con, "connections")

        # Connect to all siblings
        s_sib = _get_connected_mifs(self.GIFs.sibling) | {self: linkcls}
        d_sib = _get_connected_mifs(other.GIFs.sibling) | {other: linkcls}
        cross_connect(s_sib, d_sib, "siblings")

        return self

    def _on_connect(self, other: ModuleInterface):
        """override to handle custom connection logic"""
        ...

    def _try_connect_down(self, other: ModuleInterface, linkcls: type[Link]) -> None:
        from faebryk.core.util import zip_moduleinterfaces

        if not isinstance(other, type(self)):
            return

        for src, dst in zip_moduleinterfaces([self], [other]):
            src.connect(dst, linkcls=linkcls)

    def _try_connect_up(self, other: ModuleInterface) -> None:
        p1 = self.get_parent()
        p2 = other.get_parent()
        if not (
            p1
            and p2
            and p1[0] is not p2[0]
            and isinstance(p1[0], type(p2[0]))
            and isinstance(p1[0], ModuleInterface)
        ):
            return

        src_m = p1[0]
        dst_m = p2[0]
        assert isinstance(dst_m, ModuleInterface)

        def _is_connected(a, b):
            assert isinstance(a, ModuleInterface)
            assert isinstance(b, ModuleInterface)
            return a.is_connected_to(b)

        connection_map = [
            (src_i, dst_i, _is_connected(src_i, dst_i))
            for src_i, dst_i in zip(src_m.NODEs.get_all(), dst_m.NODEs.get_all())
        ]

        if not all(connected for _, _, connected in connection_map):
            return

        # decide which LinkType to use here
        # depends on connections between src_i & dst_i
        # e.g. if any Shallow, we need to choose shallow
        link = _resolve_link(
            [type(sublink) for _, _, sublink in connection_map if sublink]
        )

        logger.debug(f"Up connect {src_m} -> {dst_m}")
        src_m.connect(dst_m, linkcls=link)  #
        # ^ this is broken after merge: "ElectricPower.connect() got an unexpected keyword argument 'linkcls'"

    def _connect_across_hierarchies(self, other: ModuleInterface, linkcls: type[Link]):
        existing_link = self.is_connected_to(other)
        if existing_link:
            if isinstance(existing_link, linkcls):
                return
            if _resolve_link([type(existing_link), linkcls]) is type(existing_link):
                return
            # TODO
            raise NotImplementedError("Overriding existing links not implemented")

        # level 0 connect
        try:
            self.GIFs.connected.connect(other.GIFs.connected, linkcls=linkcls)
        except LinkFilteredException:
            return

        logger.debug(f"{' '*2*_CONNECT_DEPTH.inc()}Connect {self} to {other}")
        self._on_connect(other)

        # level +1 (down) connect
        self._try_connect_down(other, linkcls=linkcls)

        # level -1 (up) connect
        self._try_connect_up(other)

        _CONNECT_DEPTH.dec()

    def get_direct_connections(self) -> set[ModuleInterface]:
        return {
            gif.node
            for gif in self.GIFs.connected.get_direct_connections()
            if isinstance(gif.node, ModuleInterface)
        }

    def connect(self, other: Self, linkcls=None) -> Self:
        # TODO consider some type of check at the end within the graph instead
        # assert type(other) is type(self)
        if linkcls is None:
            linkcls = LinkDirect
        return self._connect_siblings_and_connections(other, linkcls=linkcls)

    def connect_via(self, bridge: Node | Sequence[Node], other: Self | None = None):
        from faebryk.library.can_bridge import can_bridge

        bridges = [bridge] if isinstance(bridge, Node) else bridge
        intf = self
        for sub_bridge in bridges:
            t = sub_bridge.get_trait(can_bridge)
            intf.connect(t.get_in())
            intf = t.get_out()

        if other:
            intf.connect(other)

    def is_connected_to(self, other: ModuleInterface):
        return self.GIFs.connected.is_connected(other.GIFs.connected)


TM = TypeVar("TM", bound="Module")


class _ModuleTrait(Generic[TM], _NodeTrait[TM]):
    ...


class ModuleTrait(_ModuleTrait["Module"]):
    ...


class Module(Node):
    @classmethod
    def GIFS(cls):
        class GIFS(Node.GIFS()):
            sibling = GraphInterfaceModuleSibling()

        return GIFS

    @classmethod
    def IFS(cls):
        class IFS(Module.NodesCls(ModuleInterface)):
            # workaround to help pylance
            def get_all(self) -> list[ModuleInterface]:
                return [cast_assert(ModuleInterface, i) for i in super().get_all()]

        return IFS

    def __init__(self) -> None:
        super().__init__()

        self.GIFs = Module.GIFS()(self)
        self.IFs = Module.IFS()(self)


TF = TypeVar("TF", bound="Footprint")


class _FootprintTrait(Generic[TF], _ModuleTrait[TF]):
    ...


class FootprintTrait(_FootprintTrait["Footprint"]):
    ...


class Footprint(Module):
    def __init__(self) -> None:
        super().__init__()


# -----------------------------------------------------------------------------
