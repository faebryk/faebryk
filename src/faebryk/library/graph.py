import logging
from typing import Callable, Iterable, TypeVar

import networkx as nx

from faebryk.library.core import GraphInterface, Node

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


def _get_connected_GIFs(nodes: Iterable[Node]) -> Iterable[GraphInterface]:
    """
    Gets GIFs from supplied Nodes.
    Then traces all connected GIFs from them to find the rest.
    """
    GIFs = {l for n in nodes for l in n.GIFs.get_all()}

    out = bfs_visit(
        lambda i: [j for l in i.connections for j in l.get_connections() if j != i],
        GIFs,
    )

    return GIFs | out


class Graph:
    def __init__(self, nodes: Iterable[Node]):
        G = nx.Graph()
        GIFs = _get_connected_GIFs(nodes)
        links = {l for i in GIFs for l in i.connections}

        assert all(map(lambda l: len(l.get_connections()) == 2, links))
        edges = [tuple(l.get_connections() + [{"link": l}]) for l in links]

        G.add_edges_from(edges)
        G.add_nodes_from(GIFs)

        self.G = G


# TODO:
# fix get_GIFs (current not return hierarchical interfaces I think)


# TODO next time:
# - just finished rendering working graph
#   - made node graph consist of GIF representative
# - Replace in render the names with node name maybe
# - after that build netlist exporter from graph
# ----
# - build graph while connecting components instead of afterwards
# - rethink extending NODES/IFS/.. for intellisense
# - repair samples & tests
