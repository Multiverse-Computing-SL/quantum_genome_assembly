import os
import tempfile
import unittest

from use_case.read_compressed_graph import read_unitigs

# Minimal valid BCALM2 FASTA content.
# Lines alternate: header (even index) / sequence (odd index).
# Header format: ">ID LN:i:N [L:from_sign:to_id:to_sign ...]"
FASTA_TWO_CONNECTED = """\
>0 LN:i:10 L:+:1:+
AAACCCGGGT
>1 LN:i:10 L:-:0:-
CCCGGGTAAA
"""

FASTA_WITH_UNCONNECTED = """\
>0 LN:i:10 L:+:1:+
AAACCCGGGT
>1 LN:i:10
CCCGGGTAAA
"""

FASTA_EMPTY = ""


class TestReadUnitigs(unittest.TestCase):
    def _write_fasta(self, content: str) -> str:
        fd, path = tempfile.mkstemp(suffix=".fa")
        with os.fdopen(fd, "w") as f:
            f.write(content)
        self._tmp_files.append(path)
        return path

    def setUp(self):
        self._tmp_files = []

    def tearDown(self):
        for path in self._tmp_files:
            if os.path.exists(path):
                os.remove(path)

    def test_returns_tuple_of_two_dicts(self):
        path = self._write_fasta(FASTA_TWO_CONNECTED)
        result = read_unitigs(path)
        self.assertIsInstance(result, tuple)
        self.assertEqual(len(result), 2)
        unitigs, unconnected = result
        self.assertIsInstance(unitigs, dict)
        self.assertIsInstance(unconnected, dict)

    def test_reads_connected_unitigs(self):
        path = self._write_fasta(FASTA_TWO_CONNECTED)
        unitigs, unconnected = read_unitigs(path)
        self.assertEqual(len(unitigs), 2)
        self.assertEqual(len(unconnected), 0)

    def test_dna_string_stored(self):
        path = self._write_fasta(FASTA_TWO_CONNECTED)
        unitigs, _ = read_unitigs(path)
        # Node 0.0 is at index i/2 = 0/2 = 0.0
        self.assertEqual(unitigs[0.0].dna, "AAACCCGGGT")

    def test_reverse_complement_stored(self):
        path = self._write_fasta(FASTA_TWO_CONNECTED)
        unitigs, _ = read_unitigs(path)
        # reverse complement of "AAACCCGGGT":
        # complement: TTTGGGCCCA, reversed: ACCCGGGTTT
        self.assertEqual(unitigs[0.0].reverse_dna, "ACCCGGGTTT")

    def test_outgoing_nodes_parsed(self):
        path = self._write_fasta(FASTA_TWO_CONNECTED)
        unitigs, _ = read_unitigs(path)
        # Node 0 has outgoing edge to node 1 with L:+:1:+
        self.assertIn(1, unitigs[0.0].outgoing_nodes)
        self.assertEqual(unitigs[0.0].outgoing_nodes[1]["from_sign"], "+")
        self.assertEqual(unitigs[0.0].outgoing_nodes[1]["to_sign"], "+")

    def test_incoming_nodes_populated(self):
        path = self._write_fasta(FASTA_TWO_CONNECTED)
        unitigs, _ = read_unitigs(path)
        # Node 1 should have incoming edge from node 0
        self.assertIn(0.0, unitigs[1].incoming_nodes)

    def test_reads_unconnected_unitig(self):
        path = self._write_fasta(FASTA_WITH_UNCONNECTED)
        unitigs, unconnected = read_unitigs(path)
        self.assertEqual(len(unconnected), 1)

    def test_unconnected_dna_stored(self):
        path = self._write_fasta(FASTA_WITH_UNCONNECTED)
        _, unconnected = read_unitigs(path)
        # FASTA line indices (0-based):
        #   0: ">0 L:+:1:+"  → match, not unconnected
        #   1: "AAACCCGGGT"  → DNA for node 0.0
        #   2: ">1 LN:i:10"  → no match, skip=1
        #   3: "CCCGGGTAAA"  → unconnected, key=(3-1)/2 = 1.0
        self.assertIn(1.0, unconnected)
        self.assertEqual(unconnected[1.0], "CCCGGGTAAA")

    def test_empty_file_returns_empty_dicts(self):
        path = self._write_fasta(FASTA_EMPTY)
        unitigs, unconnected = read_unitigs(path)
        self.assertEqual(unitigs, {})
        self.assertEqual(unconnected, {})

    def test_file_not_found_raises(self):
        with self.assertRaises(FileNotFoundError):
            read_unitigs("/nonexistent/path/file.fa")

    def test_invalid_extension_raises(self):
        fd, path = tempfile.mkstemp(suffix=".txt")
        os.close(fd)
        self._tmp_files.append(path)
        with self.assertRaises(ValueError):
            read_unitigs(path)

    def test_path_traversal_raises(self):
        with self.assertRaises((ValueError, FileNotFoundError)):
            read_unitigs("../../../etc/passwd")

    def test_path_outside_base_dir_raises(self):
        path = self._write_fasta(FASTA_TWO_CONNECTED)
        with tempfile.TemporaryDirectory() as other_dir:
            with self.assertRaises(ValueError):
                read_unitigs(path, base_dir=other_dir)

    def test_valid_path_within_base_dir(self):
        fd, path = tempfile.mkstemp(suffix=".fa", dir=tempfile.gettempdir())
        with os.fdopen(fd, "w") as f:
            f.write(FASTA_TWO_CONNECTED)
        self._tmp_files.append(path)
        unitigs, _ = read_unitigs(path, base_dir=tempfile.gettempdir())
        self.assertEqual(len(unitigs), 2)


if __name__ == "__main__":
    unittest.main()
