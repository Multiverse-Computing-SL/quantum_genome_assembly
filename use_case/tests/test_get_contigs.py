import unittest
from unittest.mock import MagicMock

try:
    from use_case.get_contigs import get_contigs
    from use_case.node_attributes import Unitigs

    _NETWORKX_AVAILABLE = True
except ImportError:
    _NETWORKX_AVAILABLE = False


def _make_unitigs(*pairs):
    """Build a dict of Unitigs from (node_id, dna) pairs."""
    unitigs = {}
    for node_id, dna in pairs:
        u = Unitigs(node_id)
        u.node_string(dna)
        u.reverse_complement(dna)
        unitigs[node_id] = u
    return unitigs


@unittest.skipUnless(_NETWORKX_AVAILABLE, "networkx not installed")
class TestGetContigs(unittest.TestCase):
    def test_none_results_returns_empty(self):
        contigs, count = get_contigs(None, k=3, unitigs={})
        self.assertEqual(contigs, [])
        self.assertEqual(count, 0)

    def test_empty_dict_results_returns_empty(self):
        contigs, count = get_contigs({}, k=3, unitigs={})
        self.assertEqual(contigs, [])
        self.assertEqual(count, 0)

    def test_single_edge_builds_contig(self):
        # k=3 → (k-1)=2 chars trimmed from second node
        # node 0: "AAACCC", node 1: "CCCTTT"
        # contig = "AAACCC" + "CTTT" (trim 2 from "CCCTTT") = "AAACCCCTTT"
        unitigs = _make_unitigs((0, "AAACCC"), (1, "CCCTTT"))
        results = {"0_1_+_+": 1}
        contigs, count = get_contigs(results, k=3, unitigs=unitigs)
        self.assertEqual(len(contigs), 1)
        self.assertEqual(contigs[0], "AAACCCCTTT")

    def test_zero_value_edge_ignored(self):
        unitigs = _make_unitigs((0, "AAACCC"), (1, "CCCTTT"))
        results = {"0_1_+_+": 0}
        contigs, count = get_contigs(results, k=3, unitigs=unitigs)
        self.assertEqual(contigs, [])

    def test_dict_input_handled(self):
        unitigs = _make_unitigs((0, "AAACCC"), (1, "CCCTTT"))
        results = {"0_1_+_+": 1}
        contigs, _ = get_contigs(results, k=3, unitigs=unitigs)
        self.assertEqual(len(contigs), 1)

    def test_non_dict_input_uses_values_attribute(self):
        unitigs = _make_unitigs((0, "AAACCC"), (1, "CCCTTT"))
        mock_results = MagicMock()
        mock_results.values = {"0_1_+_+": 1}
        contigs, _ = get_contigs(mock_results, k=3, unitigs=unitigs)
        self.assertEqual(len(contigs), 1)

    def test_variables_without_four_parts_ignored(self):
        unitigs = _make_unitigs((0, "AAACCC"), (1, "CCCTTT"))
        # 3-part key should be ignored
        results = {"0_1_+": 1, "0_1_+_+": 1}
        contigs, _ = get_contigs(results, k=3, unitigs=unitigs)
        self.assertEqual(len(contigs), 1)

    def test_two_edge_chain_concatenates(self):
        # k=4 → (k-1)=3 chars trimmed from each subsequent node.
        # Use sequences with proper 3-char overlaps so the expected result is clear:
        #   node 0: "AAAGGG" — last 3: "GGG"
        #   node 1: "GGGTTT" — first 3 overlap "GGG"; "GGGTTT"[3:] = "TTT"
        #   node 2: "TTTCCC" — first 3 overlap "TTT"; "TTTCCC"[3:] = "CCC"
        # Expected: "AAAGGG" + "TTT" + "CCC" = "AAAGGGTTTCCC"
        unitigs = _make_unitigs((0, "AAAGGG"), (1, "GGGTTT"), (2, "TTTCCC"))
        results = {"0_1_+_+": 1, "1_2_+_+": 1}
        contigs, count = get_contigs(results, k=4, unitigs=unitigs)
        self.assertEqual(len(contigs), 1)
        self.assertEqual(contigs[0], "AAAGGGTTTCCC")

    def test_num_multi_var_contigs_counted(self):
        # A chain of 3 nodes = 2 edges = qualifies as multi-var contig
        unitigs = _make_unitigs((0, "AAACCCC"), (1, "CCCCGGG"), (2, "CGGGTTTT"))
        results = {"0_1_+_+": 1, "1_2_+_+": 1}
        _, count = get_contigs(results, k=4, unitigs=unitigs)
        self.assertEqual(count, 1)

    def test_num_multi_var_contigs_not_counted_for_single_edge(self):
        unitigs = _make_unitigs((0, "AAACCC"), (1, "CCCTTT"))
        results = {"0_1_+_+": 1}
        _, count = get_contigs(results, k=3, unitigs=unitigs)
        self.assertEqual(count, 0)

    def test_reverse_strand_uses_reverse_dna(self):
        # node 1 reverse_dna = reverse complement of "CCCTTT"
        # complement: GGGAAA, reversed: AAAGGG
        # with k=3, trim 2 from "AAAGGG" → "AGGG"
        unitigs = _make_unitigs((0, "AAACCC"), (1, "CCCTTT"))
        results = {"0_1_+_-": 1}
        contigs, _ = get_contigs(results, k=3, unitigs=unitigs)
        self.assertEqual(len(contigs), 1)
        self.assertEqual(contigs[0], "AAACCCAGGG")

    def test_two_independent_edges_produce_two_contigs(self):
        unitigs = _make_unitigs((0, "AAACCC"), (1, "CCCTTT"), (2, "GGGAAA"), (3, "AAATTT"))
        results = {"0_1_+_+": 1, "2_3_+_+": 1}
        contigs, _ = get_contigs(results, k=3, unitigs=unitigs)
        self.assertEqual(len(contigs), 2)

    def test_circular_path_produces_one_contig(self):
        # Create a 2-node cycle: 0→1→0 (handled by circular path logic)
        unitigs = _make_unitigs((0, "AAACCC"), (1, "CCCTTT"))
        results = {"0_1_+_+": 1, "1_0_+_+": 1}
        contigs, _ = get_contigs(results, k=3, unitigs=unitigs)
        # Should produce at least one contig without infinite loop
        self.assertGreaterEqual(len(contigs), 1)


if __name__ == "__main__":
    unittest.main()
