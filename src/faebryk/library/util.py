# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging
from typing import Callable, Dict, Iterable, List, Type, TypeVar

from faebryk.libs.util import flatten

logger = logging.getLogger("library")

# TODO this file should not exist

from faebryk.library.core import Component, Interface, Link


def default_with(given, default):
    if given is not None:
        return given
    return default


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


def get_all_interfaces(obj: Component, if_type: Type[T]) -> List[T]:
    assert issubclass(if_type, Interface)

    out = [i for i in obj.IFs.get_all() if isinstance(i, if_type)]
    out.extend(
        flatten([get_all_interfaces(cmp, if_type) for cmp in obj.CMPs.get_all()])
    )

    return out


def get_all_components(component: Component) -> list[Component]:
    out = component.CMPs.get_all()
    out.extend([i for nested in out for i in get_all_components(nested)])
    return out


def get_components_of_interfaces(interfaces: list[Interface]) -> list[Component]:
    from faebryk.library.traits.interface import is_part_of_component

    out = [
        i.get_trait(is_part_of_component).get_component()
        for i in interfaces
        if i.has_trait(is_part_of_component)
    ]
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


def get_all_interfaces_link(link: Link) -> List[Interface]:
    return [i for c in link.get_connections() for i in c]


def connect_interfaces_via_chain(
    start: Interface, bridges: Iterable[Component], end: Interface
):
    from faebryk.library.traits.component import can_bridge

    end = start
    for bridge in bridges:
        end.connect(bridge.get_trait(can_bridge).get_in())
        end = bridge.get_trait(can_bridge).get_out()
    end.connect(end)


def connect_all_interfaces(interfaces: List[Interface]):
    for i in interfaces:
        for j in interfaces:
            i.connect(j)


def connect_to_all_interfaces(source: Interface, targets: Iterable[Interface]):
    for i in targets:
        source.connect(i)
