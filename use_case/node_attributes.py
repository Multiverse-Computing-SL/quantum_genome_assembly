"""Data class representing a unitig (compressed k-mer path) in the de Bruijn graph."""


class Unitigs:
    """
    This class allows each unitig to be identified by its id number.
    The dna string, reverse complement dna string, all the incoming nodes and all the outgoing nodes
    can be accessed by calling their respective attributes.
    """

    def __init__(self, node_id):
        self.dna = None
        self.reverse_dna = None
        self.outgoing_nodes = {}
        self.incoming_nodes = {}
        self.node_id = node_id

    def get_all_outgoing_nodes(self, to_id, from_sign, to_sign):
        self.outgoing_nodes[to_id] = {"from_sign": from_sign, "to_sign": to_sign}

    def get_all_incoming_nodes(self, from_id, from_sign, to_sign):
        self.incoming_nodes[from_id] = {"from_sign": from_sign, "to_sign": to_sign}

    def node_string(self, dna_string):
        self.dna = dna_string

    def reverse_complement(self, dna_string):
        complement = {"A": "T", "T": "A", "C": "G", "G": "C"}
        invalid_bases = set(dna_string) - complement.keys()
        if invalid_bases:
            raise ValueError(f"Invalid base(s) in DNA string: {invalid_bases}")
        reverse = dna_string[::-1]
        self.reverse_dna = "".join(complement[base] for base in reverse)
