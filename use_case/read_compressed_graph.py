"""Parser for BCALM 2 FASTA output; extracts unitigs and their edge relationships."""

import re
from pathlib import Path

from use_case.node_attributes import Unitigs

_ALLOWED_SUFFIXES = {".fa", ".fasta"}

MAX_NODES = 10_000
MAX_EDGES_PER_NODE = 10  # de Bruijn graph: at most 4 outgoing edges per k-mer


def _validate_fasta_path(filepath, base_dir=None):
    path = Path(filepath).resolve()
    if path.suffix.lower() not in _ALLOWED_SUFFIXES:
        raise ValueError(f"Only FASTA files (.fa, .fasta) are accepted, got: '{filepath}'")
    if base_dir is not None:
        base = Path(base_dir).resolve()
        try:
            path.relative_to(base)
        except ValueError as exc:
            raise ValueError(f"Path '{path}' is outside allowed directory '{base}'") from exc
    if not path.is_file():
        raise FileNotFoundError(f"The file '{filepath}' does not exist")
    return path


def read_unitigs(filepath, base_dir=None):
    """
    This function reads a fasta file created by BCALM 2 that contains all the unitigs of the
    compacted de Bruijn graph.
    It returns a dictionary object whose keys are the ids of the unitigs and the values are instances of the
    Unitigs class.
    """
    path = _validate_fasta_path(filepath, base_dir=base_dir)

    unitigs_kmer = {}
    unconnected_unitigs = {}
    pattern = r"L:([-+]):(\d+):([-+])"

    skip = 0
    with open(path, "r") as sequence_file:
        for i, line in enumerate(sequence_file):
            if skip == 1:
                unconnected_unitigs[(i - 1) / 2] = line.strip()
                skip = 0
                continue
            if i % 2 == 0:
                line = line.strip()
                matches = re.findall(pattern, line)

                if matches:
                    if len(matches) > MAX_EDGES_PER_NODE:
                        raise ValueError(
                            f"Node at line {i} has {len(matches)} edges, "
                            f"exceeding the limit of {MAX_EDGES_PER_NODE}."
                        )
                    if len(unitigs_kmer) >= MAX_NODES and i / 2 not in unitigs_kmer:
                        raise ValueError(f"Graph exceeds the maximum of {MAX_NODES} nodes.")
                    if i / 2 in unitigs_kmer:
                        [
                            unitigs_kmer[i / 2].get_all_outgoing_nodes(
                                int(match[1]), match[0], match[2]
                            )
                            for match in matches
                        ]

                    else:
                        unitigs_kmer[i / 2] = Unitigs(i / 2)
                        [
                            unitigs_kmer[i / 2].get_all_outgoing_nodes(
                                int(match[1]), match[0], match[2]
                            )
                            for match in matches
                        ]

                    for match in matches:
                        to_id = int(match[1])
                        if to_id in unitigs_kmer:
                            unitigs_kmer[to_id].get_all_incoming_nodes(i / 2, match[0], match[2])

                        else:
                            unitigs_kmer[to_id] = Unitigs(to_id)
                            unitigs_kmer[to_id].get_all_incoming_nodes(i / 2, match[0], match[2])

                else:
                    skip = 1

            else:
                line = line.strip()
                unitigs_kmer[(i - 1) / 2].node_string(line)
                unitigs_kmer[(i - 1) / 2].reverse_complement(line)

    return unitigs_kmer, unconnected_unitigs
