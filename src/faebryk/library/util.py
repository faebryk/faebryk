# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging
from typing import Callable, Dict, Iterable, List, TypeVar

from faebryk.library.library.interfaces import ModuleInterface

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
