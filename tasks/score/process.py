from pathlib import Path
from time import perf_counter
from typing import NamedTuple
from itaxotools.common.utility import AttrDict
from tempfile import TemporaryDirectory

from ..common.types import Results


def initialize():
    import itaxotools

    itaxotools.progress_handler("Initializing...")
    import core  # noqa
    import itaxotools.taxi2.sequences  # noqa
    import itaxotools.spart_parser  # noqa


def execute(
    concordance_path: Path,
    output_path: Path,
) -> Results:
    from core import read_latlons_from_spart, read_latlons_from_tabfile, read_morphometrics_from_tabfile, process_polygons, process_coocurrences, process_haplostats, process_morphometrics_multiple
    from itaxotools.taxi2.sequences import SequenceHandler, Sequences
    from itaxotools.taxi2.files import is_tabfile
    from itaxotools.spart_parser import Spart
    from itaxotools.asapy import PartitionAnalysis

    ts = perf_counter()

    spart = Spart.fromXML(subset_path)

    pass

    spart.toXML(output_path)

    tf = perf_counter()

    return Results(output_path, tf - ts)
