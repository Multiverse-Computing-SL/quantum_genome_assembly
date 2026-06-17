import sys
import unittest
from unittest.mock import MagicMock, patch

# ---------------------------------------------------------------------------
# Inject mock for singularity before any use_case import that depends on it.
# ---------------------------------------------------------------------------
sys.modules.setdefault("singularity", MagicMock())
sys.modules.setdefault("singularity.optimization_backend", MagicMock())
sys.modules.setdefault("singularity.optimization_backend.solvers", MagicMock())
sys.modules.setdefault("singularity.optimization_backend.encoders", MagicMock())

from use_case.compressed_solvers import Compressed_Solver  # noqa: E402


class TestCompressedSolver(unittest.TestCase):
    def setUp(self):
        # Patch Map_to_SOP so we don't need a real FASTA file
        self._map_patcher = patch("use_case.compressed_solvers.Map_to_SOP")
        MockMapToSOP = self._map_patcher.start()
        self._mock_map_instance = MagicMock()
        mock_model = MagicMock()
        mock_model.num_variables = 5
        self._mock_map_instance.build_model.return_value = mock_model
        MockMapToSOP.return_value = self._mock_map_instance

        # Patch the solver classes and sop in the module under test.
        # This targets the names as bound in compressed_solvers.py's namespace,
        # which is what's used at call time regardless of sys.modules state.
        self._sa_patcher = patch("use_case.compressed_solvers.SASolver")
        self._mqi_patcher = patch("use_case.compressed_solvers.MQISolver")
        self._sop_patcher = patch("use_case.compressed_solvers.sop")

        self.MockSASolver = self._sa_patcher.start()
        self.MockMQISolver = self._mqi_patcher.start()
        self.MockSOP = self._sop_patcher.start()

        # Configure ExhaustiveSolver via the sop mock
        self.MockSOP.solvers.ExhaustiveSolver = MagicMock()
        # Configure DefaultPenaltySolver via the sop mock
        self.MockSOP.solvers.DefaultPenaltySolver = MagicMock()

        self.solver = Compressed_Solver("fake_path.fa", k_value=21)

    def tearDown(self):
        self._map_patcher.stop()
        self._sa_patcher.stop()
        self._mqi_patcher.stop()
        self._sop_patcher.stop()

    def test_init_calls_build_model(self):
        self._mock_map_instance.build_model.assert_called_once()

    def test_k_value_stored(self):
        self.assertEqual(self.solver.k, 21)

    def test_simulated_annealing_calls_default_penalty_solver(self):
        mock_run = MagicMock()
        self.MockSOP.solvers.DefaultPenaltySolver.return_value.run = mock_run
        self.solver.simulated_annealing(num_of_samples=10)
        mock_run.assert_called_once()

    def test_simulated_annealing_passes_num_samples(self):
        mock_run = MagicMock()
        self.MockSOP.solvers.DefaultPenaltySolver.return_value.run = mock_run
        self.solver.simulated_annealing(num_of_samples=10)
        _, kwargs = mock_run.call_args
        self.assertEqual(kwargs.get("num_samples"), 10)

    def test_simulated_annealing_returns_result(self):
        mock_result = MagicMock()
        self.MockSOP.solvers.DefaultPenaltySolver.return_value.run.return_value = mock_result
        result = self.solver.simulated_annealing(num_of_samples=5)
        self.assertEqual(result, mock_result)

    def test_tensor_network_calls_mqi_solver(self):
        mock_run = MagicMock()
        self.MockMQISolver.return_value.run = mock_run
        self.solver.tensor_network()
        mock_run.assert_called_once()

    def test_tensor_network_passes_num_samples(self):
        mock_run = MagicMock()
        self.MockMQISolver.return_value.run = mock_run
        self.solver.tensor_network(num_samples=30)
        _, kwargs = mock_run.call_args
        self.assertEqual(kwargs.get("num_samples"), 30)

    def test_tensor_network_default_num_samples(self):
        mock_run = MagicMock()
        self.MockMQISolver.return_value.run = mock_run
        self.solver.tensor_network()
        _, kwargs = mock_run.call_args
        self.assertEqual(kwargs.get("num_samples"), 50)

    def test_dwave_qpu_calls_mqi_solver(self):
        # dwave_qpu calls sop.solvers.MQISolver(), not the directly imported MQISolver
        mock_run = MagicMock()
        self.MockSOP.solvers.MQISolver.return_value.run = mock_run
        self.solver.dwave_qpu(num_of_samples=50)
        mock_run.assert_called_once()

    def test_dwave_qpu_passes_num_samples(self):
        mock_run = MagicMock()
        self.MockSOP.solvers.MQISolver.return_value.run = mock_run
        self.solver.dwave_qpu(num_of_samples=25)
        _, kwargs = mock_run.call_args
        self.assertEqual(kwargs.get("num_samples"), 25)

    def test_exhaustive_solver_calls_exhaustive_solver(self):
        mock_run = MagicMock()
        self.MockSOP.solvers.ExhaustiveSolver.return_value.run = mock_run
        self.solver.exhaustive_solver()
        mock_run.assert_called_once()

    def test_exhaustive_solver_returns_result(self):
        mock_result = MagicMock()
        self.MockSOP.solvers.ExhaustiveSolver.return_value.run.return_value = mock_result
        result = self.solver.exhaustive_solver()
        self.assertEqual(result, mock_result)


if __name__ == "__main__":
    unittest.main()
