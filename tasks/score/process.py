from pathlib import Path
from time import perf_counter

from ..common.types import Results
from .types import OpenResults


def initialize():
    import itaxotools

    itaxotools.progress_handler("Initializing...")
    import core  # noqa
    import itaxotools.taxi2.sequences  # noqa
    import itaxotools.spart_parser  # noqa


def open_spart(path: Path):
    from itaxotools.spart_parser import Spart

    if not path.is_file():
        return OpenResults({}, {})

    spart = Spart.fromXML(path)

    spartition_data: dict[str, list[str]] = {}
    concordance_data: dict[str, dict[str, object]] = {}

    for spartition in spart.getSpartitions():
        concordances = spart.getSpartitionConcordances(spartition)
        spartition_data[spartition] = concordances
        for concordance in concordances:
            data = spart.getConcordanceData(spartition, concordance)
            if concordance not in concordance_data:
                concordance_data[concordance] = data
            else:
                assert concordance_data[concordance] == data

    return OpenResults(spartition_data, concordance_data)


def execute(
    concordance_path: Path,
    output_path: Path,
) -> Results:
    from itaxotools.spart_parser import Spart

    ts = perf_counter()

    spart = Spart.fromXML(concordance_path)

    pass

    spart.toXML(output_path)

    tf = perf_counter()

    return Results(output_path, tf - ts)
