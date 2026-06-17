"""Reconstructs DNA contigs from solver output by chaining selected edges."""

import networkx as nx


def get_contigs(results, k, unitigs):
    """
    Generate contigs from the solver solution using a directed graph (NetworkX).

    Each solver edge 'n1_n2_s1_s2' is a directed link from oriented unitig
    (n1, s1) to (n2, s2).  Chains are recovered in O(n) by locating in-degree-0
    heads and following successors, rather than the O(n²) greedy scan used
    previously.  Circular paths (no in-degree-0 node) are handled by choosing
    an arbitrary start and tracking visited nodes.
    """

    def get_pair_of_edges_in_solution():
        if results is None:
            return None
        elif type(results) is dict:
            return [
                key
                for key, value in results.items()
                if value == 1 and len(str(key).split("_")) == 4
            ]
        else:
            solution_dict = results.values
            return [
                key
                for key, value in solution_dict.items()
                if value == 1 and len(str(key).split("_")) == 4
            ]

    solution = get_pair_of_edges_in_solution()
    if not solution:
        return [], 0

    solution = list(map(str, solution))

    def node_dna(node_id, strand):
        idx = int(float(node_id))
        return unitigs[idx].dna if strand == "+" else unitigs[idx].reverse_dna

    # Build a directed graph: nodes are (unitig_id, strand) oriented unitig instances.
    # An edge (n1, s1) -> (n2, s2) means the solver placed unitig n1 (in orientation s1)
    # immediately before unitig n2 (in orientation s2), sharing a (k-1)-mer overlap.
    G = nx.DiGraph()
    for edge_str in solution:
        n1, n2, s1, s2 = edge_str.split("_")
        G.add_edge((n1, s1), (n2, s2))

    contigs = []
    num_multi_var_contigs = 0

    # Each weakly-connected component is an independent chain (or circular path).
    for component in nx.weakly_connected_components(G):
        sub = G.subgraph(component)

        # Chain heads are nodes with no incoming edges in this component.
        heads = [n for n in sub.nodes() if sub.in_degree(n) == 0]

        if not heads:
            # Circular contig: every node has a predecessor, so pick any start.
            heads = [next(iter(component))]

        for head in heads:
            parts = [node_dna(*head)]
            current = head
            visited = {current}

            while True:
                succs = list(sub.successors(current))
                if not succs or succs[0] in visited:
                    break
                current = succs[0]
                visited.add(current)
                # Trim the (k-1) overlap that was already contributed by the
                # previous unitig before appending the new sequence.
                parts.append(node_dna(*current)[k - 1 :])

            # A contig spans (len(parts) - 1) solver variables (edges).
            if len(parts) - 1 >= 2:
                num_multi_var_contigs += 1

            contigs.append("".join(parts))

    return contigs, num_multi_var_contigs
