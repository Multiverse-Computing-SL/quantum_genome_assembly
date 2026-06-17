import unittest

from use_case.node_attributes import Unitigs


class TestUnitigs(unittest.TestCase):
    def test_init_defaults(self):
        u = Unitigs(42)
        self.assertEqual(u.node_id, 42)
        self.assertIsNone(u.dna)
        self.assertIsNone(u.reverse_dna)
        self.assertEqual(u.outgoing_nodes, {})
        self.assertEqual(u.incoming_nodes, {})

    def test_node_string(self):
        u = Unitigs(0)
        u.node_string("ATCG")
        self.assertEqual(u.dna, "ATCG")

    def test_reverse_complement_simple(self):
        u = Unitigs(0)
        u.reverse_complement("ATCG")
        # reverse of complement: complement(ATCG)=TAGC, reversed=CGAT
        self.assertEqual(u.reverse_dna, "CGAT")

    def test_reverse_complement_all_bases(self):
        u = Unitigs(0)
        u.reverse_complement("AATTCCGG")
        # complement: TTAAGGCC, reversed: CCGGAATT
        self.assertEqual(u.reverse_dna, "CCGGAATT")

    def test_reverse_complement_single_base(self):
        u = Unitigs(0)
        for base, expected in [("A", "T"), ("T", "A"), ("C", "G"), ("G", "C")]:
            u.reverse_complement(base)
            self.assertEqual(u.reverse_dna, expected)

    def test_get_all_outgoing_nodes(self):
        u = Unitigs(0)
        u.get_all_outgoing_nodes(5, "+", "-")
        self.assertIn(5, u.outgoing_nodes)
        self.assertEqual(u.outgoing_nodes[5], {"from_sign": "+", "to_sign": "-"})

    def test_get_all_incoming_nodes(self):
        u = Unitigs(0)
        u.get_all_incoming_nodes(3, "-", "+")
        self.assertIn(3, u.incoming_nodes)
        self.assertEqual(u.incoming_nodes[3], {"from_sign": "-", "to_sign": "+"})

    def test_multiple_outgoing_nodes(self):
        u = Unitigs(0)
        u.get_all_outgoing_nodes(1, "+", "+")
        u.get_all_outgoing_nodes(2, "+", "-")
        u.get_all_outgoing_nodes(3, "-", "+")
        self.assertEqual(len(u.outgoing_nodes), 3)
        self.assertEqual(u.outgoing_nodes[2]["to_sign"], "-")

    def test_multiple_incoming_nodes(self):
        u = Unitigs(0)
        u.get_all_incoming_nodes(10, "+", "+")
        u.get_all_incoming_nodes(11, "-", "-")
        self.assertEqual(len(u.incoming_nodes), 2)

    def test_outgoing_node_overwrites_on_duplicate_id(self):
        u = Unitigs(0)
        u.get_all_outgoing_nodes(5, "+", "+")
        u.get_all_outgoing_nodes(5, "-", "-")
        self.assertEqual(len(u.outgoing_nodes), 1)
        self.assertEqual(u.outgoing_nodes[5], {"from_sign": "-", "to_sign": "-"})


if __name__ == "__main__":
    unittest.main()
