import logging
from types import NoneType
from typing import Any, List, Set, Tuple

import networkx as nx

from faebryk.library.core import Interface, LinkSibling, Node, SelfInterface
from faebryk.library.library.interfaces import Electrical
from faebryk.library.library.links import LinkDirect

logger = logging.getLogger(__name__)


def merge(G: nx.Graph, root: Interface, group: List[Interface]) -> nx.Graph:
    Gout = nx.Graph(G.subgraph([n for n in G.nodes if n not in group]))
    assert root not in group
    assert root in G.nodes, f"{root} not in {G.nodes}"
    assert all(map(lambda n: n in G.nodes, group))

    edges: List[Tuple[Any, Any]] = []
    for n in group:
        for e in G[n]:
            data = G.get_edge_data(n, e)
            # only to the outside
            if e in group or e == root:
                continue
            # connection to representative
            edges.append((e, data))

    Gout.add_edges_from([(root, e, d) for e, d in edges])
    # print("Merge:", len(G.nodes), root, len(group), "->", len(Gout.nodes))
    return Gout


def get_all_llifs(node: Node) -> List[Interface]:
    out = node.LLIFs.get_all()
    for c in node.LLIFs.children.connections:
        for i in c.get_connections():
            if i.node == node:
                continue
            if i.node is None:
                continue
            out.extend(get_all_llifs(i.node))
    return out


def get_connections(root_if: Interface) -> List[Interface]:
    return [i for c in root_if.connections for i in c.get_connections() if i != root_if]


def node_graph(G: nx.Graph, level: int, disc: type) -> nx.Graph:
    top_nodes: Set[Node] = set()
    # find top
    for i in G.nodes:
        assert isinstance(i, Interface)
        n = i.node
        if n is None:
            continue
        # find top-level nodes
        if len(G[n.LLIFs.parent]) != 1:
            continue
        targets = [n]
        for i in range(level):
            targets = [
                i.node
                for _n in targets
                for i in get_connections(_n.LLIFs.children)
                if i.node is not None and i.node != _n
            ]
        for t in targets:
            top_nodes.add(t)

    print(f"Top nodes (level={level}):{[type(n).__name__ for n in top_nodes]}")
    Gout = G
    for r in top_nodes:
        Gout = merge(
            Gout, r.LLIFs.self, [i for i in get_all_llifs(r) if i != r.LLIFs.self]
        )
    return Gout


def render_graph(G: nx.Graph, ax=None):
    import matplotlib.pyplot as plt

    for t0, t1, d in G.edges(data=True):
        assert isinstance(d, dict)

        link = d["link"]
        color = None
        weight = 1
        if isinstance(link, LinkSibling):
            color = "#000000"
            weight = 100
        elif isinstance(link, LinkDirect) and isinstance(
            link.get_connections()[0].node, Electrical
        ):
            color = "#00FF00"
            weight = 1
        else:
            color = "#FF0000"
            weight = 40

        d["color"] = color
        d["weight"] = weight

    # Draw
    layout = nx.spring_layout(G)
    nx.draw_networkx_nodes(G, ax=ax, pos=layout, node_size=150)
    nx.draw_networkx_edges(
        G,
        ax=ax,
        pos=layout,
        # edgelist=G.edges,
        edge_color=[c for _, __, c in G.edges.data("color")]
        # edge_color=color_edges_by_type(G.edges(data=True)),
    )

    # nx.draw_networkx_edges(
    #    G, pos=layout, edgelist=intra_comp_edges, edge_color="#0000FF"
    # )

    nodes: List[Interface] = G.nodes
    vertex_names = {
        vertex: f"{type(vertex.node).__name__}.{vertex.name}"
        + (
            f"|{vertex.node.get_full_name()}"
            if isinstance(vertex, SelfInterface) and vertex.node is not None
            else ""
        )
        for vertex in nodes
    }
    nx.draw_networkx_labels(G, ax=ax, pos=layout, labels=vertex_names, font_size=10)

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


def render_sidebyside(G: nx.Graph):
    import matplotlib.pyplot as plt

    X = 3

    # fig = plt.figure()
    fig, axs = plt.subplots(1, X + 1)
    fig.subplots_adjust(0, 0, 1, 1)
    # plt.subplot(111)
    for i in range(X):
        nG = node_graph(G, i, NoneType)
        render_graph(nG, ax=axs[i])

    render_graph(G, ax=axs[-1])
    return plt