import logging
from typing import Callable, Dict, Iterable, List, Set, Tuple, TypeVar

import networkx as nx

from faebryk.library.core import Interface, Link, LinkSibling, Node
from faebryk.library.library.interfaces import Electrical
from faebryk.library.library.links import LinkDirect

logger = logging.getLogger("graph")

# def _get_llifs_of_nodes(nodes: Iterable[Node]) -> Iterable[Interface]:
#    llifs = []
#    for node in nodes:
#        _llifs = node.LLIFs.get_all()
#
#        subnodes = node.NODEs.get_all()
#        if isinstance(node, Module):
#            subnodes.extend(node.IFs.get_all())
#
#        _llifs.extend(_get_llifs_of_nodes(subnodes))
#        llifs.extend(_llifs)
#    return llifs

T = TypeVar("T")


def bfs(neighbours: Callable[[T], List[T]], nodes: Iterable[T]) -> Set[T]:
    queue: List[T] = list(nodes)
    visited: Set[T] = set(queue)

    while queue:
        m = queue.pop(0)

        for neighbour in neighbours(m):
            if neighbour not in visited:
                visited.add(neighbour)
                queue.append(neighbour)

    return visited


def _get_llifs_of_nodes(nodes: Iterable[Node]) -> Iterable[Interface]:
    llifs = set([l for n in nodes for l in n.LLIFs.get_all()])

    out = bfs(
        lambda i: [j for l in i.connections for j in l.get_connections() if j != i],
        llifs,
    )

    return llifs.union(out)


def make_graph_from_nodes(nodes: Iterable[Node]) -> nx.Graph:

    G = nx.Graph()
    llifs = _get_llifs_of_nodes(nodes)
    links = set([l for i in llifs for l in i.connections])

    assert all(map(lambda l: len(l.get_connections()) == 2, links))
    edges = [tuple(l.get_connections() + [{"link": l}]) for l in links]

    G.add_edges_from(edges)
    G.add_nodes_from(llifs)

    return G


def render_graph(G: nx.Graph):
    import matplotlib.pyplot as plt

    def color_edges_by_type(edges: List[Tuple[Interface, Interface, Dict[str, Link]]]):
        def lookup(link: Link):
            if isinstance(link, LinkSibling):
                return "#000000"
            if isinstance(link, LinkDirect):
                sub = link.get_connections()[0]
                if isinstance(sub.node, Electrical):
                    return "#00FF00"
            return "#FF0000"

        return [lookup(l["link"]) for t0, t1, l in edges]

    # Draw
    plt.subplot(121)
    layout = nx.spring_layout(G)
    nx.draw_networkx_nodes(G, pos=layout, node_size=150)
    nx.draw_networkx_edges(
        G,
        pos=layout,
        edgelist=G.edges,
        edge_color=color_edges_by_type(G.edges(data=True)),
    )

    # nx.draw_networkx_edges(
    #    G, pos=layout, edgelist=intra_comp_edges, edge_color="#0000FF"
    # )

    nodes: List[Interface] = G.nodes
    vertex_names = {
        vertex: f"{type(vertex.node).__name__}.{vertex.name}" for vertex in nodes
    }
    nx.draw_networkx_labels(G, pos=layout, labels=vertex_names, font_size=6)

    # nx.draw_networkx_edge_labels(
    #    G,
    #    pos=layout,
    #    edge_labels=intra_edge_dict,
    #    font_size=10,
    #    rotate=False,
    #    bbox=dict(fc="blue"),
    #    font_color="white",
    # )

    return plt
