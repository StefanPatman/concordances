from pathlib import Path
from time import perf_counter
from collections import defaultdict

from .types import Results


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

    subset_table: dict[str, dict[str, str]] = defaultdict(dict)
    score_table: dict[str, dict[str, float | bool]] = defaultdict(dict)

    spart = Spart.fromXML(concordance_path)

    individual_list = spart.getIndividuals()

    for spartition in spart.getSpartitions():
        table = {individual: None for individual in individual_list}

        for subset in spart.getSpartitionSubsets(spartition):
            for individual in spart.getSubsetIndividuals(spartition, subset):
                table[individual] = subset

        subset_table[spartition] = table

        data = spart.getSpartitionData(spartition)

        def get_score_float(data: dict, label: str) -> float | None:
            value = data.get(label, None)
            if isinstance(value, str):
                value = float(value)
            return value

        def get_score_bool(data: dict, label: str) -> bool | None:
            value = data.get(label, None)
            if isinstance(value, str):
                if value == "Yes":
                    return True
                if value == "No":
                    return False
            return value

        score_table[spartition]["asap"] = get_score_float(data, "spartitionScore")
        score_table[spartition]["CSU"] = get_score_float(data, "CSU")
        score_table[spartition]["CSW"] = get_score_float(data, "CSW")
        score_table[spartition]["CSWC"] = get_score_float(data, "CSWC")
        score_table[spartition]["CC"] = get_score_bool(data, "CC")
        score_table[spartition]["HC"] = get_score_bool(data, "HC")

    tf = perf_counter()

    return Results(individual_list, subset_table, score_table, tf - ts)
