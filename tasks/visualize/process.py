from pathlib import Path
from time import perf_counter

from ..common.types import Results


def initialize():
    import itaxotools

    itaxotools.progress_handler("Initializing...")
    import core  # noqa
    import itaxotools.taxi2.sequences  # noqa
    import itaxotools.spart_parser  # noqa


def execute(
    concordance_path: Path,
) -> Results:
    from itaxotools.spart_parser import Spart

    ts = perf_counter()

    spart = Spart.fromXML(concordance_path)

    for spartition in spart.getSpartitions():
        pass

    tf = perf_counter()

    return Results(None, tf - ts)
