# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging
import math
from enum import Enum
from typing import (
    Callable,
    Iterable,
    Sequence,
    SupportsFloat,
    cast,
)

from faebryk.core.core import (
    Graph,
    GraphInterface,
    GraphInterfaceHierarchical,
    GraphInterfaceSelf,
    Link,
    LinkNamedParent,
    Module,
    ModuleInterface,
    Node,
    Parameter,
    Trait,
)
from faebryk.library.ANY import ANY
from faebryk.library.can_bridge_defined import can_bridge_defined
from faebryk.library.Constant import Constant
from faebryk.library.Electrical import Electrical
from faebryk.library.has_overriden_name_defined import has_overriden_name_defined
from faebryk.library.Range import Range
from faebryk.library.Set import Set
from faebryk.library.TBD import TBD
from faebryk.libs.util import NotNone, cast_assert, round_str
from typing_extensions import deprecated

logger = logging.getLogger(__name__)

# Parameter ----------------------------------------------------------------------------


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


def enum_parameter_representation(param: Parameter, required: bool = False) -> str:
    if isinstance(param, Constant):
        return param.value.name if isinstance(param.value, Enum) else str(param.value)
    elif isinstance(param, Range):
        return (
            f"{enum_parameter_representation(param.min)} - "
            f"{enum_parameter_representation(param.max)}"
        )
    elif isinstance(param, Set):
        return f"Set({', '.join(map(enum_parameter_representation, param.params))})"
    elif isinstance(param, TBD):
        return "TBD" if required else ""
    elif isinstance(param, ANY):
        return "ANY" if required else ""
    else:
        return type(param).__name__


def as_unit(
    param: Parameter, unit: str, base: int = 1000, required: bool = False
) -> str:
    if isinstance(param, Constant):
        return get_unit_prefix(param.value, base=base) + unit
    elif isinstance(param, Range):
        return (
            as_unit(param.min, unit, base=base)
            + " - "
            + as_unit(param.max, unit, base=base, required=True)
        )
    elif isinstance(param, Set):
        return (
            "Set("
            + ", ".join(map(lambda x: as_unit(x, unit, required=True), param.params))
            + ")"
        )
    elif isinstance(param, TBD):
        return "TBD" if required else ""
    elif isinstance(param, ANY):
        return "ANY" if required else ""

    raise ValueError(f"Unsupported {param=}")


def as_unit_with_tolerance(
    param: Parameter, unit: str, base: int = 1000, required: bool = False
) -> str:
    if isinstance(param, Constant):
        return as_unit(param, unit, base=base)
    elif isinstance(param, Range):
        center, delta = param.as_center_tuple()
        delta_percent = round_str(delta / center * 100, 2)
        return (
            f"{as_unit(center, unit, base=base, required=required)} ±{delta_percent}%"
        )
    elif isinstance(param, Set):
        return (
            "Set("
            + ", ".join(
                map(lambda x: as_unit_with_tolerance(x, unit, base), param.params)
            )
            + ")"
        )
    elif isinstance(param, TBD):
        return "TBD" if required else ""
    elif isinstance(param, ANY):
        return "ANY" if required else ""
    raise ValueError(f"Unsupported {param=}")


def get_parameter_max(param: Parameter):
    if isinstance(param, Constant):
        return param.value
    if isinstance(param, Range):
        return param.max
    if isinstance(param, Set):
        return max(map(get_parameter_max, param.params))
    raise ValueError(f"Can't get max for {param}")


# --------------------------------------------------------------------------------------

# Graph Querying -----------------------------------------------------------------------


def bfs_node(node: Node, filter: Callable[[GraphInterface], bool]):
    return get_nodes_from_gifs(node.get_graph().bfs_visit(filter, [node.GIFs.self]))


def get_nodes_from_gifs(gifs: Iterable[GraphInterface]):
    return {gif.node for gif in gifs}
    # TODO what is faster
    # return {n.node for n in gifs if isinstance(n, GraphInterfaceSelf)}


# Make all kinds of graph filtering functions so we can optimize them in the future
# Avoid letting user query all graph nodes always because quickly very slow


def node_projected_graph(g: Graph) -> set[Node]:
    """
    Don't call this directly, use get_all_nodes_by/of/with instead
    """
    return get_nodes_from_gifs(g.subgraph_type(GraphInterfaceSelf))


@deprecated("Use get_node_children_all")
def get_all_nodes(node: Node, include_root=False) -> list[Node]:
    return get_node_children_all(node, include_root=include_root)


def get_node_children_all(node: Node, include_root=True) -> list[Node]:
    # TODO looks like get_node_tree is 2x faster

    out = bfs_node(
        node,
        lambda x: isinstance(x, (GraphInterfaceSelf, GraphInterfaceHierarchical))
        and x is not node.GIFs.parent,
    )

    if not include_root:
        out.remove(node)

    return list(out)


def get_all_modules(node: Node) -> set[Module]:
    return {n for n in get_all_nodes(node) if isinstance(n, Module)}


@deprecated("Use node_projected_graph or get_all_nodes_by/of/with")
def get_all_nodes_graph(g: Graph):
    return node_projected_graph(g)


def get_all_nodes_with_trait[T: Trait](
    g: Graph, trait: type[T]
) -> list[tuple[Node, T]]:
    return [
        (n, n.get_trait(trait)) for n in node_projected_graph(g) if n.has_trait(trait)
    ]


# Waiting for python to add support for type mapping
def get_all_nodes_with_traits[*Ts](
    g: Graph, traits: tuple[*Ts]
):  # -> list[tuple[Node, tuple[*Ts]]]:
    return [
        (n, tuple(n.get_trait(trait) for trait in traits))
        for n in node_projected_graph(g)
        if all(n.has_trait(trait) for trait in traits)
    ]


def get_all_nodes_by_names(g: Graph, names: Iterable[str]) -> list[tuple[Node, str]]:
    return [
        (n, node_name)
        for n in node_projected_graph(g)
        if (node_name := n.get_full_name()) in names
    ]


def get_all_nodes_of_type[T: Node](g: Graph, t: type[T]) -> set[T]:
    return {n for n in node_projected_graph(g) if isinstance(n, t)}


def get_all_nodes_of_types(g: Graph, t: tuple[type[Node], ...]) -> set[Node]:
    return {n for n in node_projected_graph(g) if isinstance(n, t)}


def get_all_connected(gif: GraphInterface) -> list[tuple[GraphInterface, Link]]:
    return list(gif.edges.items())


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


def get_children[T: Node](
    node: Node,
    direct_only: bool,
    types: type[T] | tuple[type[T], ...] = Node,
    include_root: bool = False,
):
    if direct_only:
        children = get_node_direct_children_(node)
        if include_root:
            children.add(node)
    else:
        children = get_node_children_all(node, include_root=include_root)

    filtered = {n for n in children if isinstance(n, types)}

    return filtered


@deprecated("Use get_node_direct_mods_or_mifs")
def get_node_direct_children(node: Node, include_mifs: bool = True):
    return get_node_direct_mods_or_mifs(node, include_mifs=include_mifs)


def get_node_direct_mods_or_mifs(node: Node, include_mifs: bool = True):
    types = (Module, ModuleInterface) if include_mifs else Module
    return get_children(node, direct_only=True, types=types)


def get_node_direct_children_(node: Node):
    return {
        gif.node
        for gif, link in node.get_graph().get_edges(node.GIFs.children).items()
        if isinstance(link, LinkNamedParent)
    }


def get_node_tree(
    node: Node,
    include_mifs: bool = True,
    include_root: bool = True,
) -> dict[Node, dict[Node, dict]]:
    out = get_node_direct_mods_or_mifs(node, include_mifs=include_mifs)

    tree = {
        n: get_node_tree(n, include_mifs=include_mifs, include_root=False) for n in out
    }

    if include_root:
        return {node: tree}
    return tree


def iter_tree_by_depth(tree: dict[Node, dict]):
    yield list(tree.keys())

    # zip iterators, but if one iterators stops producing, the rest continue
    def zip_exhaust(*args):
        while True:
            out = [next(a, None) for a in args]
            out = [a for a in out if a]
            if not out:
                return

            yield out

    for level in zip_exhaust(*[iter_tree_by_depth(v) for v in tree.values()]):
        # merge lists of parallel subtrees
        yield [n for subtree in level for n in subtree]


def get_mif_tree(
    obj: ModuleInterface | Module,
) -> dict[ModuleInterface, dict[ModuleInterface, dict]]:
    mifs = get_children(obj, direct_only=True, types=ModuleInterface)

    return {mif: get_mif_tree(mif) for mif in mifs}


def format_mif_tree(tree: dict[ModuleInterface, dict[ModuleInterface, dict]]) -> str:
    def str_tree(
        tree: dict[ModuleInterface, dict[ModuleInterface, dict]],
    ) -> dict[str, dict]:
        def get_name(k: ModuleInterface):
            # get_parent never none, since k gotten from parent
            return NotNone(k.get_parent())[1]

        return {
            f"{get_name(k)} ({type(k).__name__})": str_tree(v) for k, v in tree.items()
        }

    import json

    return json.dumps(str_tree(tree), indent=4)


# --------------------------------------------------------------------------------------

# Connection utils ---------------------------------------------------------------------


def connect_interfaces_via_chain(
    start: ModuleInterface, bridges: Iterable[Node], end: ModuleInterface
):
    from faebryk.library.can_bridge import can_bridge

    last = start
    for bridge in bridges:
        last.connect(bridge.get_trait(can_bridge).get_in())
        last = bridge.get_trait(can_bridge).get_out()
    last.connect(end)


def connect_all_interfaces[MIF: ModuleInterface](interfaces: Iterable[MIF]):
    interfaces = list(interfaces)
    if not interfaces:
        return
    return connect_to_all_interfaces(interfaces[0], interfaces[1:])
    # not needed with current connection implementation
    # for i in interfaces:
    #    for j in interfaces:
    #        i.connect(j)


def connect_to_all_interfaces[MIF: ModuleInterface](
    source: MIF, targets: Iterable[MIF]
):
    for i in targets:
        source.connect(i)
    return source


def zip_connect_modules(src: Iterable[Module] | Module, dst: Iterable[Module] | Module):
    for src_m, dst_m in zip_moduleinterfaces(src, dst):
        src_m.connect(dst_m)


def zip_moduleinterfaces(
    src: Iterable[ModuleInterface | Module] | ModuleInterface | Module,
    dst: Iterable[ModuleInterface | Module] | ModuleInterface | Module,
):
    if isinstance(src, Node):
        src = [src]
    if isinstance(dst, Node):
        dst = [dst]

    # TODO check types?
    for src_m, dst_m in zip(src, dst):
        src_m_children = {
            NotNone(n.get_parent())[1]: n
            for n in get_children(src_m, direct_only=True, types=ModuleInterface)
        }
        dst_m_children = {
            NotNone(n.get_parent())[1]: n
            for n in get_children(dst_m, direct_only=True, types=ModuleInterface)
        }
        assert src_m_children.keys() == dst_m_children.keys()

        for k, src_i in src_m_children.items():
            dst_i = dst_m_children[k]
            yield src_i, dst_i


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


# --------------------------------------------------------------------------------------

# Specialization -----------------------------------------------------------------------


def specialize_interface[T: ModuleInterface](
    general: ModuleInterface,
    special: T,
) -> T:
    logger.debug(f"Specializing MIF {general} with {special}")

    # This is doing the heavy lifting
    general.connect(special)

    # Establish sibling relationship
    general.GIFs.specialized.connect(special.GIFs.specializes)

    return special


def specialize_module[T: Module](
    general: Module,
    special: T,
    matrix: list[tuple[ModuleInterface, ModuleInterface]] | None = None,
    attach_to: Node | None = None,
) -> T:
    logger.debug(f"Specializing Module {general} with {special}" + " " + "=" * 20)

    def get_node_prop_matrix[U: Node](sub_type: type[U]) -> list[tuple[U, U]]:
        def _get_with_names(module: Module) -> dict[str, U]:
            if sub_type is ModuleInterface:
                holder = module.IFs
            elif sub_type is Parameter:
                holder = module.PARAMs
            elif sub_type is Node:
                holder = module.NODEs
            else:
                raise Exception()

            return {NotNone(i.get_parent())[1]: i for i in holder.get_all()}

        s = _get_with_names(general)
        d = _get_with_names(special)

        matrix = [
            (src_i, dst_i)
            for name, src_i in s.items()
            if (dst_i := d.get(name)) is not None
        ]

        return matrix

    if matrix is None:
        matrix = get_node_prop_matrix(ModuleInterface)

        # TODO add warning if not all src interfaces used

    param_matrix = get_node_prop_matrix(Parameter)

    for src, dst in matrix:
        specialize_interface(src, dst)

    for src, dst in param_matrix:
        dst.merge(src)

    # TODO this cant work
    # for t in general.traits:
    #    # TODO needed?
    #    if special.has_trait(t.trait):
    #        continue
    #    special.add_trait(t)

    general.GIFs.specialized.connect(special.GIFs.specializes)
    logger.debug("=" * 120)

    # Attach to new parent
    has_parent = special.get_parent() is not None
    assert not has_parent or attach_to is None
    if not has_parent:
        if attach_to:
            attach_to.NODEs.extend_list("specialized", special)
        else:
            gen_parent = general.get_parent()
            if gen_parent:
                setattr(gen_parent[0].NODEs, f"{gen_parent[1]}_specialized", special)

    return special


# --------------------------------------------------------------------------------------


# Hierarchy queries --------------------------------------------------------------------


def get_parent(node: Node, filter_expr: Callable):
    candidates = [p for p, _ in node.get_hierarchy() if filter_expr(p)]
    if not candidates:
        return None
    return candidates[-1]


def get_parent_of_type[T: Node](node: Node, parent_type: type[T]) -> T | None:
    return cast(parent_type, get_parent(node, lambda p: isinstance(p, parent_type)))


def get_parent_with_trait[TR: Trait](node: Node, trait: type[TR]):
    for parent, _ in reversed(node.get_hierarchy()):
        if parent.has_trait(trait):
            return parent, parent.get_trait(trait)
    raise ValueError("No parent with trait found")


def get_children_of_type[U: Node](node: Node, child_type: type[U]) -> list[U]:
    return list(get_children(node, direct_only=False, types=child_type))


def get_first_child_of_type[U: Node](node: Node, child_type: type[U]) -> U:
    for level in iter_tree_by_depth(get_node_tree(node)):
        for child in level:
            if isinstance(child, child_type):
                return child
    raise ValueError("No child of type found")


# --------------------------------------------------------------------------------------


def use_interface_names_as_net_names(node: Node, name: str | None = None):
    from faebryk.library.Net import Net

    if not name:
        p = node.get_parent()
        assert p
        name = p[1]

    name_prefix = node.get_full_name()

    el_ifs = {n for n in get_all_nodes(node) if isinstance(n, Electrical)}

    # for el_if in el_ifs:
    #    print(el_if)
    # print("=" * 80)

    # performance
    resolved: set[ModuleInterface] = set()

    # get representative interfaces that determine the name of the Net
    to_use: set[Electrical] = set()
    for el_if in el_ifs:
        # performance
        if el_if in resolved:
            continue

        connections = el_if.get_direct_connections() | {el_if}

        # skip ifs with Nets
        if matched_nets := {  # noqa: F841
            n
            for c in connections
            if (p := c.get_parent())
            and isinstance(n := p[0], Net)
            and n.IFs.part_of in connections
        }:
            # logger.warning(f"Skipped, attached to Net: {el_if}: {matched_nets!r}")
            resolved.update(connections)
            continue

        group = {mif for mif in connections if mif in el_ifs}

        # heuristic: choose shortest name
        picked = min(group, key=lambda x: len(x.get_full_name()))
        to_use.add(picked)

        # for _el_if in group:
        #    print(_el_if if _el_if is not picked else f"{_el_if} <-")
        # print("-" * 80)

        # performance
        resolved.update(group)

    nets: dict[str, tuple[Net, Electrical]] = {}
    for el_if in to_use:
        net_name = f"{name}{el_if.get_full_name().removeprefix(name_prefix)}"

        # name collision
        if net_name in nets:
            net, other_el = nets[net_name]
            raise Exception(
                f"{el_if} resolves to {net_name} but not connected"
                + f"\nwhile attaching nets to {node}={name} (connected via {other_el})"
                + "\n"
                + "\nConnections\n\t"
                + "\n\t".join(map(str, el_if.get_direct_connections()))
                + f"\n{'-'*80}"
                + "\nNet Connections\n\t"
                + "\n\t".join(map(str, net.IFs.part_of.get_direct_connections()))
            )

        net = Net()
        net.add_trait(has_overriden_name_defined(net_name))
        net.IFs.part_of.connect(el_if)
        logger.debug(f"Created {net_name} for {el_if}")
        nets[net_name] = net, el_if
