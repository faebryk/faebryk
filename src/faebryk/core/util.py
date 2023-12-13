# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging
import math
from typing import Callable, Iterable, Sequence, SupportsFloat, TypeVar, cast

import networkx as nx

# TODO this file should not exist
from faebryk.core.core import (
    GraphInterface,
    GraphInterfaceSelf,
    Link,
    Module,
    ModuleInterface,
    Node,
    Parameter,
)
from faebryk.library.can_bridge_defined import can_bridge_defined
from faebryk.library.Constant import Constant
from faebryk.library.Electrical import Electrical
from faebryk.library.Range import Range
from faebryk.library.Set import Set
from faebryk.libs.util import NotNone, cast_assert

logger = logging.getLogger(__name__)
T = TypeVar("T")


def as_scientific(value: SupportsFloat, base=10):
    if value == 0:
        return 0, 0
    exponent = math.floor(math.log(abs(value), base))
    mantissa = value / (base**exponent)

    return mantissa, exponent


def unit_map(
    value: SupportsFloat,
    units: Sequence[str],
    start: str | None = None,
    base: int = 1000,
    allow_out_of_bounds: bool = False,
):
    value = float(value)
    start_idx = units.index(start) if start is not None else 0

    mantissa, exponent = as_scientific(value, base=base)

    available_exponent = max(min(exponent + start_idx, len(units) - 1), 0) - start_idx
    exponent_difference = exponent - available_exponent

    if not allow_out_of_bounds and exponent_difference:
        raise ValueError(f"Value {value} with {exponent=} out of bounds for {units=}")

    effective_mantissa = mantissa * (base**exponent_difference)
    round_digits = round(math.log(base, 10) * (1 - exponent_difference))
    # print(f"{exponent_difference=}, {effective_mantissa=}, {round_digits=}")

    idx = available_exponent + start_idx
    rounded_mantissa = round(effective_mantissa, round_digits)
    if rounded_mantissa == math.floor(rounded_mantissa):
        rounded_mantissa = math.floor(rounded_mantissa)

    out = f"{rounded_mantissa}{units[idx]}"

    return out


def get_unit_prefix(value: SupportsFloat, base: int = 1000):
    if base == 1000:
        units = ["f", "p", "n", "µ", "m", "", "k", "M", "G", "T", "P", "E"]
    elif base == 1024:
        units = ["", "Ki", "Mi", "Gi", "Ti", "Pi", "Ei"]
    else:
        raise NotImplementedError(f"Unsupported {base=}")

    return unit_map(value, units, start="", base=base, allow_out_of_bounds=True)


def as_unit(value: SupportsFloat, unit: str, base: int = 1000):
    return get_unit_prefix(value, base=base) + unit


def is_type_set_subclasses(type_subclasses: set[type], types: set[type]) -> bool:
    hits = {t: any(issubclass(s, t) for s in type_subclasses) for t in types}
    return all(hits.values()) and all(
        any(issubclass(s, t) for t in types) for s in hits
    )


def get_all_nodes(node: Node, order_types=None) -> list[Node]:
    if order_types is None:
        order_types = []

    out: list[Node] = list(node.NODEs.get_all())
    out.extend([i for nested in out for i in get_all_nodes(nested)])

    out = sorted(
        out,
        key=lambda x: order_types.index(type(x))
        if type(x) in order_types
        else len(order_types),
    )

    return out


def get_all_modules(node: Node) -> list[Module]:
    return [n for n in get_all_nodes(node) if isinstance(n, Module)]


def get_all_nodes_graph(G: nx.Graph):
    return {
        n
        for gif in G.nodes
        if isinstance(gif, GraphInterfaceSelf) and (n := gif.node) is not None
    }


def get_all_highest_parents_graph(G: nx.Graph):
    return {n for n in get_all_nodes_graph(G) if n.GIFs.parent.get_parent() is None}


def get_all_connected(gif: GraphInterface) -> list[tuple[GraphInterface, Link]]:
    return [
        (other, link)
        for link in gif.connections
        for other in link.get_connections()
        if other is not gif
    ]


def get_connected_mifs(gif: GraphInterface):
    return set(get_connected_mifs_with_link(gif).keys())


def get_connected_mifs_with_link(gif: GraphInterface):
    assert isinstance(gif.node, ModuleInterface)
    connections = get_all_connected(gif)

    # check if ambiguous links between mifs
    assert len(connections) == len({c[0] for c in connections})

    return {
        cast_assert(ModuleInterface, s.node): link
        for s, link in connections
        if s.node is not gif.node
    }


def get_net(mif: Electrical):
    from faebryk.library.Net import Net

    nets = {
        net
        for mif in get_connected_mifs(mif.GIFs.connected)
        if (net := get_parent_of_type(mif, Net)) is not None
    }

    if not nets:
        return None

    assert len(nets) == 1
    return next(iter(nets))


def get_parent(node: Node, filter_expr: Callable):
    candidates = [p for p, _ in node.get_hierarchy() if filter_expr(p)]
    if not candidates:
        return None
    return candidates[-1]


T = TypeVar("T")


def get_parent_of_type(node: Node, parent_type: type[T]) -> T | None:
    return cast(parent_type, get_parent(node, lambda p: isinstance(p, parent_type)))


def connect_interfaces_via_chain(
    start: ModuleInterface, bridges: Iterable[Node], end: ModuleInterface
):
    from faebryk.library.can_bridge import can_bridge

    last = start
    for bridge in bridges:
        last.connect(bridge.get_trait(can_bridge).get_in())
        last = bridge.get_trait(can_bridge).get_out()
    last.connect(end)


def connect_all_interfaces(interfaces: Iterable[ModuleInterface]):
    interfaces = list(interfaces)
    if not interfaces:
        return
    return connect_to_all_interfaces(interfaces[0], interfaces[1:])
    # not needed with current connection implementation
    # for i in interfaces:
    #    for j in interfaces:
    #        i.connect(j)


def connect_to_all_interfaces(
    source: ModuleInterface, targets: Iterable[ModuleInterface]
):
    for i in targets:
        source.connect(i)
    return source


def zip_connect_modules(src: Iterable[Module], dst: Iterable[Module]):
    for src_m, dst_m in zip(src, dst):
        for src_i, dst_i in zip(src_m.IFs.get_all(), dst_m.IFs.get_all()):
            assert isinstance(src_i, ModuleInterface)
            assert isinstance(dst_i, ModuleInterface)
            src_i.connect(dst_i)


def zip_moduleinterfaces(
    src: Iterable[ModuleInterface], dst: Iterable[ModuleInterface]
):
    # TODO check names?
    # TODO check types?
    for src_m, dst_m in zip(src, dst):
        for src_i, dst_i in zip(src_m.NODEs.get_all(), dst_m.NODEs.get_all()):
            assert isinstance(src_i, ModuleInterface)
            assert isinstance(dst_i, ModuleInterface)
            yield src_i, dst_i


def get_mif_tree(
    obj: ModuleInterface | Module,
) -> dict[ModuleInterface, dict[ModuleInterface, dict]]:
    mifs = obj.IFs.get_all() if isinstance(obj, Module) else obj.NODEs.get_all()
    assert all(isinstance(i, ModuleInterface) for i in mifs)
    mifs = cast(list[ModuleInterface], mifs)

    return {mif: get_mif_tree(mif) for mif in mifs}


def format_mif_tree(tree: dict[ModuleInterface, dict[ModuleInterface, dict]]) -> str:
    def str_tree(
        tree: dict[ModuleInterface, dict[ModuleInterface, dict]]
    ) -> dict[str, dict]:
        def get_name(k: ModuleInterface):
            # get_parent never none, since k gotten from parent
            return NotNone(k.get_parent())[1]

        return {
            f"{get_name(k)} ({type(k).__name__})": str_tree(v) for k, v in tree.items()
        }

    import json

    return json.dumps(str_tree(tree), indent=4)


T = TypeVar("T", bound=ModuleInterface)


def specialize_interface(
    general: ModuleInterface,
    special: T,
) -> T:
    logger.debug(f"Specializing MIF {general} with {special}")

    # This is doing the heavy lifting
    general.connect(special)

    # Establish sibling relationship
    general.GIFs.sibling.connect(special.GIFs.sibling)

    return special


T = TypeVar("T", bound=Module)


def specialize_module(
    general: Module,
    special: T,
    matrix: list[tuple[ModuleInterface, ModuleInterface]] | None = None,
) -> T:
    logger.debug(f"Specializing Module {general} with {special}" + " " + "=" * 20)

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

        specialize_interface(src, dst)

    for t in general.traits:
        # TODO needed?
        if special.has_trait(t.trait):
            continue
        special.add_trait(t)

    general.GIFs.sibling.connect(special.GIFs.sibling)
    logger.debug("=" * 120)

    return special


def get_parameter_max(param: Parameter):
    if isinstance(param, Constant):
        return param.value
    if isinstance(param, Range):
        return param.max
    if isinstance(param, Set):
        return max(map(get_parameter_max, param.params))
    raise ValueError(f"Can't get max for {param}")


def reversed_bridge(bridge: Node):
    from faebryk.library.can_bridge import can_bridge

    class _reversed_bridge(Node):
        def __init__(self) -> None:
            super().__init__()

            bridge_trait = bridge.get_trait(can_bridge)
            if_in = bridge_trait.get_in()
            if_out = bridge_trait.get_out()

            self.add_trait(can_bridge_defined(if_out, if_in))

    return _reversed_bridge()
