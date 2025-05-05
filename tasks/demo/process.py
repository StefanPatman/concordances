from pathlib import Path
from time import perf_counter
from typing import NamedTuple



class Results(NamedTuple):
    output_path: Path
    seconds_taken: float


def initialize():
    import itaxotools

    itaxotools.progress_handler("Initializing...")
    import core  # noqa
    import itaxotools.taxi2.sequences  # noqa
    import itaxotools.spart_parser  # noqa


def execute(
    spart_path: Path,
    sequence_path: Path,
    output_path: Path,
) -> Results:
    import warnings

    from core import process_polygons, process_coocurrences, process_haplostats
    from itaxotools.taxi2.sequences import SequenceHandler, Sequences
    from itaxotools.spart_parser import Spart

    ts = perf_counter()

    spart = Spart.fromXML(spart_path)
    sequences = Sequences.fromPath(sequence_path, SequenceHandler.Fasta)
    process_polygons(spart)
    process_coocurrences(spart, 5.0)
    process_haplostats(spart, sequences)
    spart.toXML(output_path)

    tf = perf_counter()

    return Results(output_path, tf - ts)
