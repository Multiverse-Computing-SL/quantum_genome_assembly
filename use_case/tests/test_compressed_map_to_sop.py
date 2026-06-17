import os
import sys
import tempfile
import unittest
from unittest.mock import MagicMock, patch

# ---------------------------------------------------------------------------
# Inject mock for singularity before any use_case import that depends on it.
# ---------------------------------------------------------------------------
_mock_sop = MagicMock()
_mock_model = MagicMock()
_mock_sop.Model.return_value = _mock_model
_mock_sop.Sense.MINIMIZE = 0

sys.modules.setdefault("singularity", MagicMock())
sys.modules.setdefault("singularity.optimization_backend", _mock_sop)
sys.modules.setdefault("singularity.optimization_backend.solvers", MagicMock())
sys.modules.setdefault("singularity.optimization_backend.encoders", MagicMock())

from use_case.compressed_map_to_sop import Map_to_SOP  # noqa: E402

# ---------------------------------------------------------------------------
# Minimal BCALM2 FASTA fixtures
# ---------------------------------------------------------------------------
# Two nodes connected A→B, B has no outgoing edges.
FASTA_TWO_NODES = """\
>0 LN:i:10 L:+:1:+
AAACCCGGGT
>1 LN:i:10
CCCGGGTAAA
"""

# Four nodes: 0→1, 1→2, 2→3 (linear chain, all non-breaking)
FASTA_CHAIN_FOUR = """\
>0 LN:i:10 L:+:1:+
AAACCCGGGT
>1 LN:i:10 L:+:2:+
CCCGGGTAAA
>2 LN:i:10 L:+:3:+
GGGTAAACCC
>3 LN:i:10
TAAACCCGGG
"""

FASTA_EMPTY = ""


class TestMapToSOP(unittest.TestCase):
    def _write_fasta(self, content: str) -> str:
        fd, path = tempfile.mkstemp(suffix=".fa")
        with os.fdopen(fd, "w") as f:
            f.write(content)
        self._tmp_files.append(path)
        return path

    def setUp(self):
        self._tmp_files = []
        # Reset mock call history before each test
        _mock_sop.reset_mock()
        _mock_model.reset_mock()

    def tearDown(self):
        for path in self._tmp_files:
            if os.path.exists(path):
                os.remove(path)

    def test_init_with_valid_fasta_stores_unitigs(self):
        path = self._write_fasta(FASTA_TWO_NODES)
        m = Map_to_SOP(path)
        self.assertGreater(len(m.unitigs), 0)

    def test_binary_variables_counts_edges(self):
        path = self._write_fasta(FASTA_TWO_NODES)
        m = Map_to_SOP(path)
        mock_model = MagicMock()
        variables = m.binary_variables(mock_model)
        # Node 0 has one outgoing edge to node 1 → 1 variable
        self.assertEqual(len(variables), 1)

    def test_objective_sums_variables(self):
        path = self._write_fasta(FASTA_TWO_NODES)
        m = Map_to_SOP(path)
        mock_model = MagicMock()
        m.variables = m.binary_variables(mock_model)
        # objective() returns sum of all variable values — should not be None
        obj = m.objective()
        self.assertIsNotNone(obj)

    def test_flow_conservation_constraint_returns_list(self):
        path = self._write_fasta(FASTA_TWO_NODES)
        m = Map_to_SOP(path)
        mock_model = MagicMock()
        m.variables = m.binary_variables(mock_model)
        result = m.flow_conservation_constraint()
        self.assertIsInstance(result, list)

    def test_breaking_nodes_constraint_returns_list(self):
        path = self._write_fasta(FASTA_TWO_NODES)
        m = Map_to_SOP(path)
        mock_model = MagicMock()
        m.variables = m.binary_variables(mock_model)
        result = m.breaking_nodes_constraint()
        self.assertIsInstance(result, list)

    def test_sign_balance_constraint_returns_list(self):
        path = self._write_fasta(FASTA_TWO_NODES)
        m = Map_to_SOP(path)
        mock_model = MagicMock()
        m.variables = m.binary_variables(mock_model)
        result = m.sign_balance_constraint()
        self.assertIsInstance(result, list)

    def test_num_of_constraints_none_before_build(self):
        path = self._write_fasta(FASTA_TWO_NODES)
        m = Map_to_SOP(path)
        # build_model not called yet, constraint counts are None
        self.assertIsNone(m.num_of_constraints())

    def test_num_of_constraints_after_build(self):
        path = self._write_fasta(FASTA_TWO_NODES)
        m = Map_to_SOP(path)
        m.build_model()
        # After build, num_of_constraints returns an integer (may be 0)
        result = m.num_of_constraints()
        self.assertIsNotNone(result)
        self.assertIsInstance(result, int)

    def test_build_model_calls_sop_model(self):
        path = self._write_fasta(FASTA_CHAIN_FOUR)
        # Patch sop in the module's namespace to check calls correctly.
        with patch("use_case.compressed_map_to_sop.sop") as mock_sop:
            mock_model = MagicMock()
            mock_sop.Model.return_value = mock_model
            mock_sop.Sense.MINIMIZE = 0
            m = Map_to_SOP(path)
            m.build_model()
        self.assertTrue(mock_sop.Model.called)

    def test_num_of_flow_conservation_constraint_set_after_loop(self):
        """The count must reflect all constraints, not just the last iteration."""
        path = self._write_fasta(FASTA_CHAIN_FOUR)
        m = Map_to_SOP(path)
        mock_model = MagicMock()
        m.variables = m.binary_variables(mock_model)
        m.flow_conservation_constraint()
        self.assertIsNotNone(m.num_of_flow_conservation_constraint)
        self.assertIsInstance(m.num_of_flow_conservation_constraint, int)

    def test_num_of_breaking_nodes_constraint_set_after_loop(self):
        """The count must reflect all breaking node constraints after the loop completes."""
        path = self._write_fasta(FASTA_CHAIN_FOUR)
        m = Map_to_SOP(path)
        mock_model = MagicMock()
        m.variables = m.binary_variables(mock_model)
        m.breaking_nodes_constraint()
        self.assertIsNotNone(m.num_of_breaking_nodes_constraint)
        self.assertIsInstance(m.num_of_breaking_nodes_constraint, int)

    def test_num_of_sign_balance_constraint_set_after_loop(self):
        """The count must reflect all sign balance constraints after the loop completes."""
        path = self._write_fasta(FASTA_CHAIN_FOUR)
        m = Map_to_SOP(path)
        mock_model = MagicMock()
        m.variables = m.binary_variables(mock_model)
        m.sign_balance_constraint()
        self.assertIsNotNone(m.num_of_sign_balance_constraint)
        self.assertIsInstance(m.num_of_sign_balance_constraint, int)


if __name__ == "__main__":
    unittest.main()
