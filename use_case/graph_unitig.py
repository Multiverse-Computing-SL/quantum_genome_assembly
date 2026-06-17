"""Visualises the compacted de Bruijn graph using Graphviz."""

import graphviz


def plot_graph(unitigs, unconnected_unitigs, max_nodes=1500):
    """
    Build a Graphviz directed graph of the compacted de Bruijn graph.

    Args:
        unitigs: dict mapping node ID -> Unitigs object (connected unitigs with edges)
        unconnected_unitigs: dict mapping node ID -> Unitigs object (isolated unitigs)
        max_nodes: maximum number of graph elements (nodes + edges) to render (default 1500)

    Returns:
        graphviz.Digraph: styled directed graph with dark background and blue nodes
    """
    dot = graphviz.Digraph()
    dot.attr(bgcolor="#151719")

    for id, node_attr in unitigs.items():
        if len(dot.body) >= max_nodes:
            break

        id = int(id)

        dot.node(str(id), style="filled", fillcolor="#38b6ff")
        connected_nodes = node_attr.outgoing_nodes

        for i, node in connected_nodes.items():
            if len(dot.body) >= max_nodes:
                break

            i = int(i)
            dot.node(str(i), style="filled", fillcolor="#38b6ff")
            dot.edge(
                str(id),
                str(i),
                color="#38b6ff",
                headlabel=node["to_sign"],
                fontcolor="white",
                taillabel=node["from_sign"],
                labelfontcolor="white",
            )

    if len(dot.body) < max_nodes:
        for i, node in unconnected_unitigs.items():
            if len(dot.body) >= max_nodes:
                break
            i = int(i)
            dot.node(str(i), style="filled", fillcolor="#38b6ff")

    return dot
