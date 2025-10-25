from pathlib import Path
from time import perf_counter
from tempfile import TemporaryDirectory

from ..common.types import Results


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
    morphometrics_path: Path | None,
    sequence_paths: list[Path],
    co_ocurrence_threshold: float,
    morphometrics_threshold: float,
    asapy_mode: bool,
    asapy_options: dict[str, object],
) -> Results:
    from core import (
        read_latlons_from_spart,
        read_latlons_from_tabfile,
        read_morphometrics_from_tabfile,
        process_polygons,
        process_coocurrences,
        process_haplostats,
        process_morphometrics_multiple,
    )
    from itaxotools.taxi2.sequences import SequenceHandler, Sequences
    from itaxotools.taxi2.files import is_tabfile
    from itaxotools.spart_parser import Spart
    from itaxotools.asapy import PartitionAnalysis

    ts = perf_counter()

    if asapy_mode:
        a = PartitionAnalysis(asapy_options.input_path)
        a.params.general.sequence_length = asapy_options.sequence_length
        a.params.advanced.number = asapy_options.number
        a.params.advanced.seuil_pvalue = asapy_options.seuil_pvalue
        a.params.advanced.seed = asapy_options.seed
        a.params.distance.method = asapy_options.method
        a.params.distance.rate = asapy_options.kimura_rate

        temp = TemporaryDirectory(prefix="asap_")
        a.target = Path(temp.name).as_posix()

        a.run()

        xml_files = list(Path(temp.name).glob("*.xml"))
        if not xml_files:
            raise Exception("ASAPy did not generate any XML files, exiting...")
        subset_path = xml_files[0]

    spart = Spart.fromXML(subset_path)

    if coord_path:
        if is_tabfile(coord_path):
            latlons = read_latlons_from_tabfile(coord_path)
        else:
            latlons = read_latlons_from_spart(coord_path)
        process_polygons(spart, latlons)
        process_coocurrences(spart, latlons, co_ocurrence_threshold)

    if morphometrics_path:
        morphometrics = read_morphometrics_from_tabfile(morphometrics_path)
        process_morphometrics_multiple(spart, morphometrics, morphometrics_threshold)

    for sequence_path in sequence_paths:
        sequences = Sequences.fromPath(sequence_path, SequenceHandler.Fasta)
        process_haplostats(spart, sequences, label=sequence_path.stem)

    spart.toXML(output_path)

    tf = perf_counter()

    return Results(output_path, tf - ts)
