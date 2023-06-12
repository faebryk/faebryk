import logging
from typing import Callable, Iterable, TypeVar

import networkx as nx

from faebryk.library.core import Interface, Node

logger = logging.getLogger(__name__)

T = TypeVar("T")


def bfs_visit(neighbours: Callable[[T], list[T]], nodes: Iterable[T]) -> set[T]:
    """
    Generic BFS (not depending on Graph)
    Returns all visited nodes.
    """
    queue: list[T] = list(nodes)
    visited: set[T] = set(queue)

    while queue:
        m = queue.pop(0)

        for neighbour in neighbours(m):
            if neighbour not in visited:
                visited.add(neighbour)
                queue.append(neighbour)

    return visited


def _get_connected_llifs(nodes: Iterable[Node]) -> Iterable[Interface]:
    """
    Gets LLIFs from supplied Nodes.
    Then traces all connected LLIFs from them to find the rest.
    """
    llifs = {l for n in nodes for l in n.LLIFs.get_all()}

    out = bfs_visit(
        lambda i: [j for l in i.connections for j in l.get_connections() if j != i],
        llifs,
    )

    return llifs | out


class Graph:
    def __init__(self, nodes: Iterable[Node]):
        G = nx.Graph()
        llifs = _get_connected_llifs(nodes)
        links = {l for i in llifs for l in i.connections}

        assert all(map(lambda l: len(l.get_connections()) == 2, links))
        edges = [tuple(l.get_connections() + [{"link": l}]) for l in links]

        G.add_edges_from(edges)
        G.add_nodes_from(llifs)

        self.G = G


# TODO:
# fix get_llifs (current not return hierarchical interfaces I think)


# TODO next time:
# - just finished rendering working graph
#   - made node graph consist of llif representative
# - Replace in render the names with node name maybe
# - after that build netlist exporter from graph
# ----
# - build graph while connecting components instead of afterwards
# - rethink extending NODES/IFS/.. for intellisense
# - repair samples & tests
