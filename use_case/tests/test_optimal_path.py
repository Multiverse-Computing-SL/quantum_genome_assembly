import unittest

try:
    import graphviz

    from use_case.optimal_path import plot_optimal_path

    _GRAPHVIZ_AVAILABLE = True
except ImportError:
    _GRAPHVIZ_AVAILABLE = False


@unittest.skipUnless(_GRAPHVIZ_AVAILABLE, "graphviz not installed")
class TestPlotOptimalPath(unittest.TestCase):
    def test_returns_digraph(self):
        result = plot_optimal_path({})
        self.assertIsInstance(result, graphviz.Digraph)

    def test_empty_dict_has_no_nodes_or_edges(self):
        # dot.attr(bgcolor=...) adds one graph-attribute entry to body,
        # so body is not empty even with no variables. Verify no nodes or edges.
        result = plot_optimal_path({})
        self.assertNotIn("->", result.source)
        self.assertNotIn("[style=filled", result.source)

    def test_bgcolor_set(self):
        result = plot_optimal_path({})
        self.assertIn("#151719", result.source)

    def test_edge_with_value_one_added(self):
        result = plot_optimal_path({"1_2_+_-": 1})
        src = result.source
        self.assertIn("1.0", src)
        self.assertIn("2.0", src)
        self.assertIn("->", src)

    def test_edge_with_value_zero_ignored(self):
        result = plot_optimal_path({"1_2_+_-": 0})
        self.assertNotIn("->", result.source)

    def test_non_four_part_key_ignored(self):
        result = plot_optimal_path({"1_2_+": 1})
        self.assertNotIn("->", result.source)

    def test_five_part_key_ignored(self):
        result = plot_optimal_path({"1_2_3_+_-": 1})
        self.assertNotIn("->", result.source)

    def test_correct_head_tail_labels(self):
        result = plot_optimal_path({"10_20_+_-": 1})
        src = result.source
        self.assertIn("+", src)
        self.assertIn("-", src)

    def test_edge_color(self):
        result = plot_optimal_path({"1_2_+_+": 1})
        self.assertIn("#38b6ff", result.source)

    def test_max_nodes_limit_respected(self):
        # Each edge iteration appends up to 3 body entries (2 nodes + 1 edge)
        # before the guard re-checks. Verify that a small limit produces far fewer
        # body entries than rendering all 100 edges without a limit would.
        variables = {f"{i}_{i + 1}_+_+": 1 for i in range(100)}
        limited = plot_optimal_path(variables, max_nodes=5)
        unlimited = plot_optimal_path(variables, max_nodes=10000)
        self.assertLess(len(limited.body), len(unlimited.body))

    def test_multiple_edges_all_added_within_limit(self):
        variables = {"0_1_+_+": 1, "2_3_-_+": 1}
        result = plot_optimal_path(variables, max_nodes=1500)
        src = result.source
        self.assertIn("0.0", src)
        self.assertIn("3.0", src)


if __name__ == "__main__":
    unittest.main()
