# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging
from typing import Callable, Dict, Iterable, List, TypeVar

from faebryk.library.library.interfaces import ModuleInterface
from faebryk.libs.util import NotNone, cast_assert

logger = logging.getLogger(__name__)

# TODO this file should not exist

from faebryk.library.core import GraphInterface, Module, Node

T = TypeVar("T")


def times(cnt: int, lamb: Callable[[], T]) -> List[T]:
    return [lamb() for _ in range(cnt)]


def unit_map(value: int, units, start=None, base=1000):
    if start is None:
        start_idx = 0
    else:
        start_idx = units.index(start)

    cur = base ** ((-start_idx) + 1)
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
        value //= base
    return value


def get_all_nodes(node: Node, order_types=None) -> list[Node]:
    if order_types is None:
        order_types = []

    out: List[Node] = list(node.NODEs.get_all())
    out.extend([i for nested in out for i in get_all_nodes(nested)])

    out = sorted(
        out,
        key=lambda x: order_types.index(type(x))
        if type(x) in order_types
        else len(order_types),
    )

    return out


def get_all_connected(gif: GraphInterface) -> list[GraphInterface]:
    return [
        other
        for l in gif.connections
        for other in l.get_connections()
        if other is not gif
    ]


def get_connected_mifs(gif: GraphInterface):
    assert isinstance(gif.node, ModuleInterface)
    return {
        cast_assert(ModuleInterface, s.node)
        for s in get_all_connected(gif)
        if s.node is not gif.node
    }


T = TypeVar("T")
U = TypeVar("U")


def get_key(haystack: Dict[T, U], needle: U) -> T:
    return find(haystack.items(), lambda x: x[1] == needle)[0]


def find(haystack: Iterable[T], needle: Callable) -> T:
    results = list(filter(needle, haystack))
    if len(results) != 1:
        raise ValueError
    return results[0]


# TODO maybe not needed for Interface
IF = TypeVar("IF", GraphInterface, ModuleInterface)


def connect_interfaces_via_chain(start: IF, bridges: Iterable[Node], end: IF):
    from faebryk.library.traits.component import can_bridge

    end = start
    for bridge in bridges:
        end.connect(bridge.get_trait(can_bridge).get_in())
        end = bridge.get_trait(can_bridge).get_out()
    end.connect(end)


def connect_all_interfaces(interfaces: List[IF]):
    for i in interfaces:
        for j in interfaces:
            i.connect(j)


def connect_to_all_interfaces(source: IF, targets: Iterable[IF]):
    for i in targets:
        source.connect(i)


def zip_connect_modules(src: Iterable[Module], dst: Iterable[Module]):
    for src_m, dst_m in zip(src, dst):
        for src_i, dst_i in zip(src_m.IFs.get_all(), dst_m.IFs.get_all()):
            assert isinstance(src_i, ModuleInterface)
            assert isinstance(dst_i, ModuleInterface)
            src_i.connect(dst_i)


T = TypeVar("T", bound=ModuleInterface)


def specialize_interface(
    general: ModuleInterface,
    special: T,
) -> T:
    # Establish sibling relationship
    general.GIFs.sibling.connect(special.GIFs.sibling)

    # Connect already connected interfaces
    for x in get_connected_mifs(general.GIFs.connected):
        x._connect(special)

    return special


T = TypeVar("T", bound=Module)


def specialize_module(
    general: Module,
    special: T,
    matrix: list[tuple[ModuleInterface, ModuleInterface]] | None = None,
) -> T:
    if matrix is None:

        def _get_with_names(module: Module) -> dict[str, ModuleInterface]:
            return {NotNone(i.get_parent())[1]: i for i in module.IFs.get_all()}

        s = _get_with_names(general)
        d = _get_with_names(special)

        matrix = [
            (src_i, dst_i)
            for name, src_i in s.items()
            if (dst_i := d.get(name)) is not None
        ]

        # TODO add warning if not all src interfaces used

    for src, dst in matrix:
        assert src in general.IFs.get_all()
        assert dst in special.IFs.get_all()

        if not type(dst) is type(src):
            specialize_interface(src, dst)
            continue

        src.connect(dst)

    for t in general.traits:
        # TODO needed?
        if special.has_trait(t.trait):
            continue
        special.add_trait(t)

    general.GIFs.sibling.connect(special.GIFs.sibling)

    return special
