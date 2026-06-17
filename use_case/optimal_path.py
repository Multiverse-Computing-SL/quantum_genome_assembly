"""Visualises the solver's selected edges (solution path) using Graphviz."""

import graphviz


def plot_optimal_path(binary_variables, max_nodes=1500):
    """
    Plots the optimal path of the binary variables. That is, how he binary variables are joined to form contigs.
    Args:
        binary_variables:

    Returns:
    """

    all_edges = [key for key, value in binary_variables.items() if value == 1]
    all_edges = [e for e in map(str, all_edges) if len(e.split("_")) == 4]

    dot = graphviz.Digraph()
    dot.attr(bgcolor="#151719")

    for edge in all_edges:
        if len(dot.body) > max_nodes:
            break
        edge_attr = edge.split("_")

        starting_node = float(edge_attr[0])
        ending_node = float(edge_attr[1])
        starting_sign = edge_attr[2]
        ending_sign = edge_attr[3]

        dot.node(str(starting_node), style="filled", fillcolor="#38b6ff")

        dot.node(str(ending_node), style="filled", fillcolor="#38b6ff")

        dot.edge(
            str(starting_node),
            str(ending_node),
            color="#38b6ff",
            headlabel=ending_sign,
            fontcolor="white",
            taillabel=starting_sign,
            labelfontcolor="white",
        )

    return dot
