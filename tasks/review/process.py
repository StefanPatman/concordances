from pathlib import Path
from time import perf_counter
from collections import defaultdict
from math import comb

from .types import SCORE_COLUMNS, STRUCTURAL_KEYS, ExportResults, Results


def initialize():
    import itaxotools

    itaxotools.progress_handler("Initializing...")
    import core  # noqa
    import itaxotools.spart_parser  # noqa


def get_score_float(data: dict, label: str) -> float | None:
    value = data.get(label, None)
    if isinstance(value, str):
        value = float(value)
    return value


def get_score_bool(data: dict, label: str) -> bool | None:
    value = data.get(label, None)
    if isinstance(value, str):
        if value in ("Yes", "True"):
            return True
        if value in ("No", "False"):
            return False
        return None
    return value


def execute(
    concordance_path: Path,
) -> Results:
    from itaxotools.spart_parser import Spart

    ts = perf_counter()

    subset_table: dict[str, dict[str, str]] = defaultdict(dict)
    score_table: dict[str, dict[str, float | bool | None]] = defaultdict(dict)

    spart = Spart.fromXML(concordance_path)

    individual_list = spart.getIndividuals()

    for spartition in spart.getSpartitions():
        table = {individual: None for individual in individual_list}

        nsub = len(spart.getSpartitionSubsets(spartition))
        nind = 0

        for subset in spart.getSpartitionSubsets(spartition):
            individuals = spart.getSubsetIndividuals(spartition, subset)
            nind += len(individuals)
            for individual in individuals:
                table[individual] = subset

        subset_table[spartition] = table

        data = spart.getSpartitionData(spartition)
        derived = {"Nind": nind, "Nsub": nsub, "Ncomp": comb(nsub, 2)}

        scores = {}
        for column in SCORE_COLUMNS:
            if column.key is None:
                scores[column.name] = derived[column.name]
            elif column.kind == "bool":
                scores[column.name] = get_score_bool(data, column.key)
            else:
                scores[column.name] = get_score_float(data, column.key)

        score_table[spartition] = scores

    tf = perf_counter()

    return Results(individual_list, dict(subset_table), dict(score_table), tf - ts)


def export(
    concordance_path: Path,
    output_path: Path,
    spartitions: list[str],
    keys: list[str],
) -> ExportResults:
    """Write a SPART file holding only the given spartitions and score keys.

    Spartitions are written in the order given, which is the order the user
    sorted them into, since the XML writer follows insertion order.
    """
    from itaxotools.spart_parser import Spart

    ts = perf_counter()

    spart = Spart.fromXML(concordance_path)

    reduced = Spart()
    for key in [
        "project_name",
        "date",
        "individuals",
        "locations",
        "location_synonyms",
    ]:
        reduced.spartDict[key] = spart.spartDict.get(key, {})

    kept = STRUCTURAL_KEYS | set(keys)

    for number, label in enumerate(spartitions, start=1):
        source = spart.getSpartitionFromLabel(label)
        reduced.spartDict["spartitions"][str(number)] = {
            key: value for key, value in source.items() if key in kept
        }

    reduced.toXML(output_path)

    tf = perf_counter()

    return ExportResults(output_path, len(spartitions), tf - ts)
