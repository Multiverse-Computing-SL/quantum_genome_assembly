"""
Genome Assembly Pipeline — CLI Entry Point

Usage:
    python main.py --reads PATH --k INT --solver SOLVER [options]

Required arguments:
    --reads     Path to the reads file (.fasta or .fastq)
    --k         K-mer size for the de Bruijn graph
    --solver    Solver to use: simulated_annealing | tensor_network | dwave_qpu | exhaustive

Optional arguments:
    --reference   Path to a reference genome (.fasta) for QUAST quality assessment
    --abundance   Minimum k-mer abundance threshold (default: 2, filters sequencing errors)
    --num-samples Number of solver samples (default: 50; tensor_network uses this too)
    --output      Output directory (default: results_YYYYMMDD_HHMMSS)

Output folder contents:
    contigs.fasta      — assembled contigs
    quast/             — QUAST quality assessment output
    unitig_graph.png   — compressed de Bruijn graph visualisation
    optimal_path.png   — solution path visualisation
    metrics.csv        — problem and quality metrics
    read.unitigs.fa    — intermediate bcalm output (kept for reproducibility)
"""

import argparse
import csv
import os
import subprocess  # nosec
import sys
import time

from use_case.compressed_map_to_sop import MAX_VARIABLES
from use_case.compressed_solvers import Compressed_Solver
from use_case.get_contigs import get_contigs
from use_case.graph_unitig import plot_graph
from use_case.optimal_path import plot_optimal_path


def parse_args():
    parser = argparse.ArgumentParser(
        description="Genome assembly pipeline using quantum/quantum-inspired solvers.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--reads", required=True, help="Path to reads file (.fasta or .fastq)")
    parser.add_argument("--k", required=True, type=int, help="K-mer size for the de Bruijn graph")
    parser.add_argument(
        "--solver",
        required=True,
        choices=["simulated_annealing", "tensor_network", "dwave_qpu", "exhaustive"],
        help="Solver backend to use",
    )
    parser.add_argument(
        "--reference",
        default=None,
        help="Path to reference genome for QUAST quality assessment (optional)",
    )
    parser.add_argument(
        "--abundance",
        type=int,
        default=2,
        help="Minimum k-mer abundance threshold (filters sequencing errors)",
    )
    parser.add_argument(
        "--num-samples",
        type=int,
        default=50,
        dest="num_samples",
        help="Number of solver samples",
    )
    parser.add_argument(
        "--output",
        default=None,
        help="Output directory (default: results_YYYYMMDD_HHMMSS)",
    )
    return parser.parse_args()


_MAX_READS_FILE_BYTES = 50 * 1024 * 1024  # 50 MB
_MAX_READS = 10_000


def _validate_reads_size(reads_path):
    """Reject reads files that are too large or contain too many sequences.

    Raises:
        SystemExit: If the file exceeds size or read-count limits.
    """
    file_size = os.path.getsize(reads_path)
    if file_size > _MAX_READS_FILE_BYTES:
        print(
            f"ERROR: Reads file is {file_size // (1024 * 1024)} MB, "
            f"exceeding the {_MAX_READS_FILE_BYTES // (1024 * 1024)} MB limit.",
            file=sys.stderr,
        )
        sys.exit(1)

    reads_path_lower = reads_path.lower()
    is_fastq = reads_path_lower.endswith(".fastq") or reads_path_lower.endswith(".fq")
    count = 0
    with open(reads_path, "r") as f:
        for i, line in enumerate(f):
            if is_fastq:
                if i % 4 == 0:  # header line of each FASTQ record
                    count += 1
            else:
                if line.startswith(">"):
                    count += 1
            if count > _MAX_READS:
                print(
                    f"ERROR: Reads file contains more than {_MAX_READS} sequences. "
                    "Reduce the number of reads before running the pipeline.",
                    file=sys.stderr,
                )
                sys.exit(1)


def compress_reads(reads_path, k, abundance, output_dir):
    """Run bcalm to compress the reads into unitigs.

    bcalm names output as <prefix>.unitigs.fa. By passing -out <output_dir>/read,
    the unitigs file is written to <output_dir>/read.unitigs.fa.

    Returns:
        str: Path to the produced unitigs FASTA file.

    Raises:
        SystemExit: If bcalm returns a non-zero exit code.
    """
    _validate_reads_size(reads_path)
    unitigs_path = os.path.join(output_dir, "read.unitigs.fa")
    command = [
        "bcalm",
        "-in",
        reads_path,
        "-kmer-size",
        str(k),
        "-abundance-min",
        str(abundance),
        "-out",
        os.path.join(output_dir, "read"),
    ]
    print(f"[1/5] Compressing reads with bcalm (k={k}, abundance-min={abundance})...")
    result = subprocess.call(  # nosec
        command, shell=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
    )
    if result != 0:
        print(
            f"ERROR: bcalm failed with exit code {result}. "
            "Check that bcalm is installed and that the reads file is valid.",
            file=sys.stderr,
        )
        sys.exit(1)
    return unitigs_path


def build_solver(unitigs_path, k, base_dir=None):
    """Instantiate the solver and build the QUBO model.

    Returns:
        Compressed_Solver: Initialised solver instance.

    Raises:
        SystemExit: If the QUBO model produces zero binary variables.
    """
    print("[2/5] Building QUBO model from unitigs...")
    solver = Compressed_Solver(unitigs_path, k, base_dir=base_dir)
    num_variables = solver.map_sop.num_of_variables or 0
    if num_variables == 0:
        print(
            "ERROR: The QUBO model has 0 binary variables. "
            "Try a different k value or reduce the number of reads.",
            file=sys.stderr,
        )
        sys.exit(1)
    if num_variables > MAX_VARIABLES:
        print(
            f"ERROR: The QUBO model has {num_variables} binary variables, "
            f"exceeding the limit of {MAX_VARIABLES}. "
            "Reduce the input size or increase the abundance threshold.",
            file=sys.stderr,
        )
        sys.exit(1)
    print(f"      Binary variables: {num_variables}")
    return solver


def run_solver(solver, solver_name, num_samples):
    """Dispatch to the selected solver and return the result with elapsed time.

    Returns:
        Tuple[OptimizationResult, float]: (solution, solver_runtime_seconds)
    """
    print(f"[3/5] Running solver: {solver_name} (num_samples={num_samples})...")
    start = time.time()
    if solver_name == "simulated_annealing":
        solution = solver.simulated_annealing(num_of_samples=num_samples)
    elif solver_name == "tensor_network":
        solution = solver.tensor_network(num_samples=num_samples)
    elif solver_name == "dwave_qpu":
        solution = solver.dwave_qpu(num_of_samples=num_samples)
    elif solver_name == "exhaustive":
        solution = solver.exhaustive_solver()
    solver_runtime = time.time() - start
    print(f"      Solver runtime: {solver_runtime:.3f}s")
    return solution, solver_runtime


def select_best_contigs(solution, k, unitigs):
    """Iterate over all samples and return the contigs from the best sample.

    The best sample is the one that maximises the average contig length, which
    is a proxy for how well the solver covered the genome.

    Returns:
        Tuple[list[str], int, object]: (contigs, num_multi_var_contigs, best_sample_obj)

    Raises:
        SystemExit: If no sample produces any contigs.
    """
    averages = []
    for sample in solution.samples:
        sample_dict = _sample_to_dict(sample)
        all_contigs, _ = get_contigs(sample_dict, k, unitigs)
        if all_contigs:
            averages.append(sum(len(s) for s in all_contigs) / len(all_contigs))
        else:
            averages.append(0.0)

    if max(averages) == 0.0:
        print(
            "ERROR: No sample produced any contigs. " "Try a different k value or solver.",
            file=sys.stderr,
        )
        sys.exit(1)

    best_idx = averages.index(max(averages))
    best_sample_obj = solution.samples[best_idx]
    best_sample_dict = _sample_to_dict(best_sample_obj)
    contigs, num_multi_var = get_contigs(best_sample_dict, k, unitigs)
    return contigs, num_multi_var, best_sample_obj, best_sample_dict


def _sample_to_dict(sample):
    """Extract the variable→value mapping from a solver sample.

    Tries the SDK's todict()["qpu_readout"] interface first, then falls back
    to the .variables attribute for older SDK versions.
    """
    try:
        return sample.todict()["qpu_readout"]
    except (AttributeError, KeyError, TypeError):
        if hasattr(sample, "variables"):
            return sample.variables
        return {}


def write_contigs(contigs, output_dir):
    """Write contigs to a FASTA file in the output directory."""
    path = os.path.join(output_dir, "contigs.fasta")
    with open(path, "w") as f:
        for i, contig in enumerate(contigs, start=1):
            f.write(f">Contig_{i}\n{contig}\n")
    return path


def get_constraint_metrics(best_sample_obj):
    """Extract constraint satisfaction counts from the best sample.

    Returns a dict with keys: all_constraints, satisfied_constraints,
    unsatisfied_constraints. Values are None if the attribute is unavailable.
    """
    try:
        satisfaction = best_sample_obj.satisfaction
        return {
            "all_constraints": len(satisfaction),
            "satisfied_constraints": int(satisfaction.sum()),
            "unsatisfied_constraints": int((~satisfaction).sum()),
        }
    except AttributeError:
        print(
            "WARNING: constraint satisfaction metrics not available "
            "(solver SDK may differ from expected version).",
            file=sys.stderr,
        )
        return {
            "all_constraints": None,
            "satisfied_constraints": None,
            "unsatisfied_constraints": None,
        }


def run_quast(contigs_fasta, output_dir, reference=None):
    """Run QUAST for quality assessment. Skips gracefully on failure."""
    quast_dir = os.path.join(output_dir, "quast")
    command = ["quast.py", "-o", quast_dir, "-m", "30", contigs_fasta]
    if reference:
        command = ["quast.py", "-o", quast_dir, "-r", reference, "-m", "30", contigs_fasta]

    print("[4/5] Running QUAST quality assessment...")
    result = subprocess.call(  # nosec
        command, shell=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
    )
    if result != 0:
        print("WARNING: QUAST exited with a non-zero code. Output may be incomplete.")
    return quast_dir


def render_graphs(unitigs, unconnected_unitigs, best_sample_dict, output_dir):
    """Render the unitig graph and solution path as PNG files."""
    unitig_graph = plot_graph(unitigs, unconnected_unitigs)
    unitig_graph.render(
        filename=os.path.join(output_dir, "unitig_graph"),
        format="png",
        cleanup=True,
    )

    path_graph = plot_optimal_path(best_sample_dict)
    path_graph.render(
        filename=os.path.join(output_dir, "optimal_path"),
        format="png",
        cleanup=True,
    )


def write_metrics(
    output_dir,
    num_binary_variables,
    constraint_metrics,
    contigs,
    num_multi_var_contigs,
    solver_runtime,
    total_time,
):
    """Write a CSV file with problem and runtime metrics."""
    path = os.path.join(output_dir, "metrics.csv")
    row = {
        "num_binary_variables": num_binary_variables,
        "num_constraints": constraint_metrics["all_constraints"],
        "satisfied_constraints": constraint_metrics["satisfied_constraints"],
        "unsatisfied_constraints": constraint_metrics["unsatisfied_constraints"],
        "num_contigs": len(contigs),
        "num_multi_var_contigs": num_multi_var_contigs,
        "solver_runtime_s": round(solver_runtime, 4),
        "total_time_s": round(total_time, 4),
    }
    with open(path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(row.keys()))
        writer.writeheader()
        writer.writerow(row)


def main():
    args = parse_args()
    total_start = time.time()

    # Validate inputs before doing any work
    if not os.path.isfile(args.reads):
        print(f"ERROR: Reads file not found: {args.reads}", file=sys.stderr)
        sys.exit(1)
    if args.reference and not os.path.isfile(args.reference):
        print(f"ERROR: Reference genome not found: {args.reference}", file=sys.stderr)
        sys.exit(1)

    # Create output directory
    output_dir = os.path.abspath(args.output or f"results_{time.strftime('%Y%m%d_%H%M%S')}")
    os.makedirs(output_dir, exist_ok=True)
    print(f"Output directory: {output_dir}")

    # Pipeline steps
    unitigs_path = compress_reads(args.reads, args.k, args.abundance, output_dir)
    solver = build_solver(unitigs_path, args.k, base_dir=output_dir)

    unitigs = solver.map_sop.unitigs
    unconnected_unitigs = solver.map_sop.unconnected_unitigs
    num_binary_variables = solver.map_sop.num_of_variables or 0

    solution, solver_runtime = run_solver(solver, args.solver, args.num_samples)

    contigs, num_multi_var_contigs, best_sample_obj, best_sample_dict = select_best_contigs(
        solution, args.k, unitigs
    )

    print(f"[4/5] Assembling outputs ({len(contigs)} contig(s))...")
    contigs_fasta = write_contigs(contigs, output_dir)
    constraint_metrics = get_constraint_metrics(best_sample_obj)
    run_quast(contigs_fasta, output_dir, reference=args.reference)
    render_graphs(unitigs, unconnected_unitigs, best_sample_dict, output_dir)

    total_time = time.time() - total_start
    write_metrics(
        output_dir,
        num_binary_variables,
        constraint_metrics,
        contigs,
        num_multi_var_contigs,
        solver_runtime,
        total_time,
    )

    print(f"[5/5] Done in {total_time:.2f}s. Results written to: {output_dir}")
    print("      contigs.fasta, quast/, unitig_graph.png, optimal_path.png, metrics.csv")
    if constraint_metrics["satisfied_constraints"] is not None:
        total = constraint_metrics["all_constraints"]
        satisfied = constraint_metrics["satisfied_constraints"]
        print(f"      Constraints: {satisfied}/{total} satisfied")


if __name__ == "__main__":
    main()
