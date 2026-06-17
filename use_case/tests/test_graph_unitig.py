import unittest

try:
    import graphviz

    from use_case.graph_unitig import plot_graph
    from use_case.node_attributes import Unitigs

    _GRAPHVIZ_AVAILABLE = True
except ImportError:
    _GRAPHVIZ_AVAILABLE = False


def _make_unitigs_with_edge(from_id, to_id, from_sign="+", to_sign="+"):
    u_from = Unitigs(from_id)
    u_from.get_all_outgoing_nodes(to_id, from_sign, to_sign)
    u_to = Unitigs(to_id)
    u_to.get_all_incoming_nodes(from_id, from_sign, to_sign)
    return {from_id: u_from, to_id: u_to}


@unittest.skipUnless(_GRAPHVIZ_AVAILABLE, "graphviz not installed")
class TestPlotGraph(unittest.TestCase):
    def test_returns_digraph(self):
        result = plot_graph({}, {})
        self.assertIsInstance(result, graphviz.Digraph)

    def test_empty_inputs_has_no_nodes_or_edges(self):
        # dot.attr(bgcolor=...) adds one graph-attribute entry to body,
        # so body is not empty even with no unitigs. Verify no nodes or edges.
        result = plot_graph({}, {})
        self.assertNotIn("->", result.source)
        self.assertNotIn("[style=filled", result.source)

    def test_bgcolor_set(self):
        result = plot_graph({}, {})
        self.assertIn("#151719", result.source)

    def test_nodes_added_for_unitigs(self):
        unitigs = _make_unitigs_with_edge(0, 1)
        result = plot_graph(unitigs, {})
        src = result.source
        self.assertIn("0", src)
        self.assertIn("1", src)

    def test_edges_added_for_outgoing_nodes(self):
        unitigs = _make_unitigs_with_edge(0, 1, "+", "-")
        result = plot_graph(unitigs, {})
        src = result.source
        # Edge from 0 to 1 should be present
        self.assertIn("-> 1", src)

    def test_edge_labels_contain_signs(self):
        unitigs = _make_unitigs_with_edge(0, 1, "+", "-")
        result = plot_graph(unitigs, {})
        src = result.source
        self.assertIn("+", src)
        self.assertIn("-", src)

    def test_unconnected_nodes_added_when_space(self):
        unconnected = {0: "AAACCC"}
        result = plot_graph({}, unconnected)
        self.assertIn("0", result.source)

    def test_max_nodes_limit_respected(self):
        # Build a 10-node chain and verify a small limit produces fewer body
        # entries than rendering the full graph without a limit.
        unitigs = {}
        for i in range(10):
            u = Unitigs(i)
            if i < 9:
                u.get_all_outgoing_nodes(i + 1, "+", "+")
            unitigs[i] = u
        limited = plot_graph(unitigs, {}, max_nodes=5)
        unlimited = plot_graph(unitigs, {}, max_nodes=1500)
        self.assertLess(len(limited.body), len(unlimited.body))

    def test_node_fill_color(self):
        unitigs = _make_unitigs_with_edge(0, 1)
        result = plot_graph(unitigs, {})
        self.assertIn("#38b6ff", result.source)


if __name__ == "__main__":
    unittest.main()
