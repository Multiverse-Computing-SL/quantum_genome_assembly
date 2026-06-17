"""Wrapper providing multiple solver backends (SA, MQI, D-Wave, exhaustive) for the QUBO problem."""

import singularity.optimization_backend as sop
from singularity.optimization_backend.solvers import MQISolver, SASolver

from use_case.compressed_map_to_sop import Map_to_SOP


class Compressed_Solver:
    """
    This class contains methods that solves the QUBO problem using different solvers.
    it calls the save_information class to store all the data from the solver in a separate folder
    """

    def __init__(self, filepath, k_value, penalty=800, base_dir=None):
        self.map_sop = Map_to_SOP(filepath, base_dir=base_dir)
        self.model = self.map_sop.build_model(penalty)
        self.k = k_value

    def simulated_annealing(self, num_of_samples):
        """
        This method solves the QUBo problem using simulated annealing
        and saves all the data from the solution in a file

        :param num_of_samples:
        :return:  OptimizationResult
        """
        solver = SASolver(sop.encoders.SpinEncoder())
        solver = sop.solvers.DefaultPenaltySolver(solver)
        results = solver.run(self.model, num_samples=num_of_samples)
        return results

    def tensor_network(self, num_samples: int = 50):
        solver = MQISolver()
        results = solver.run(self.model, num_samples=num_samples)
        return results

    def dwave_qpu(self, num_of_samples):
        """
        This method solves the QUBO problem using the dwave quantum processor
        and saves all the data from the solution in a file

        :param num_of_samples:
        :return:  OptimizationResult
        """

        results = sop.solvers.MQISolver().run(self.model, num_samples=num_of_samples)

        return results

    def exhaustive_solver(self):
        """
        This method solves the QUBO problem using an exhaustive solver
        and saves all the data from the solution in a file

        :return:  OptimizationResult
        """
        if self.model.num_variables > 30:
            raise ValueError("Exhaustive solver is not feasible for more than 30 variables.")
        else:
            results = sop.solvers.ExhaustiveSolver().run(self.model)

        return results
