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
    subset_path: Path,
    output_path: Path,
    coord_path: Path | None,
    sequence_path: Path | None,
    morphometrics_path: Path | None,
) -> Results:
    from core import read_latlons_from_spart, read_latlons_from_tabfile, read_morphometrics_from_tabfile, process_polygons, process_coocurrences, process_haplostats, process_morphometrics_multiple
    from itaxotools.taxi2.sequences import SequenceHandler, Sequences
    from itaxotools.taxi2.files import is_tabfile
    from itaxotools.spart_parser import Spart

    ts = perf_counter()

    spart = Spart.fromXML(subset_path)

    if coord_path:
        if is_tabfile(coord_path):
            latlons = read_latlons_from_tabfile(coord_path)
        else:
            latlons = read_latlons_from_spart(coord_path)
        process_polygons(spart, latlons)
        process_coocurrences(spart, latlons, 5.0)

    if sequence_path:
        sequences = Sequences.fromPath(sequence_path, SequenceHandler.Fasta)
        process_haplostats(spart, sequences)

    if morphometrics_path:
        morphometrics = read_morphometrics_from_tabfile(morphometrics_path)
        process_morphometrics_multiple(spart, morphometrics)

    spart.toXML(output_path)

    tf = perf_counter()

    return Results(output_path, tf - ts)
