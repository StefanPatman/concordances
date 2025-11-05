from pathlib import Path
from time import perf_counter
import math
from collections import defaultdict

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

    concordance_data: dict[str, dict[str, object]] = {}

    for spartition in spart.getSpartitions():
        concordances = spart.getSpartitionConcordances(spartition)
        for concordance in concordances:
            data = spart.getConcordanceData(spartition, concordance)
            if concordance not in concordance_data:
                concordance_data[concordance] = data
            else:
                assert concordance_data[concordance] == data

    individuals_list = spart.getIndividuals()

    return OpenResults(concordance_data, individuals_list)


def execute(
    concordance_path: Path,
    output_path: Path,
    concordance_weights: dict[str, float],
    evidence_types_weights: dict[str, float],
    evidence_types_behaviours: dict[str, bool],
    conspecific_constraints: list[list[str]],
    heterospecific_constraints: list[list[str]],
) -> Results:
    from itaxotools.spart_parser import Spart

    print(f"{concordance_weights=}")
    print(f"{evidence_types_weights=}")
    print(f"{evidence_types_behaviours=}")
    print(f"{conspecific_constraints=}")
    print(f"{heterospecific_constraints=}")

    ts = perf_counter()

    spart = Spart.fromXML(concordance_path)

    for spartition in spart.getSpartitions():
        subsets = spart.getSpartitionSubsets(spartition)
        if len(subsets) < 2:
            continue

        score: int = 0
        score_c: float = 0.0
        support_table: dict[tuple[int, int], float] = defaultdict(lambda: 0.0)
        support_table_cap: dict[tuple[int, int], int] = defaultdict(lambda: 0)
        combinations = math.comb(len(subsets), 2)
        evidence_types_totals: dict[str, int] = defaultdict(lambda: 0)
        concordance_evidence_types: dict[str, str] = {}
        final_concordance_weights: dict[str, float] = {}

        for concordance in spart.getSpartitionConcordances(spartition):
            if concordance not in concordance_weights:
                continue
            data = spart.getConcordanceData(spartition, concordance)
            evidence_type = data["evidenceType"]
            concordance_evidence_types[concordance] = evidence_type
            evidence_types_totals[evidence_type] += concordance_weights[concordance]

        for concordance, weight in concordance_weights.items():
            evidence_type = concordance_evidence_types[concordance]
            weight *= evidence_types_weights[evidence_type]
            if not evidence_types_behaviours[evidence_type]:
                weight /= evidence_types_totals[evidence_type]
            final_concordance_weights[concordance] = weight

        for concordance in spart.getSpartitionConcordances(spartition):
            if concordance not in concordance_weights:
                continue
            for limit in spart.getConcordantLimits(spartition, concordance):
                sub_a = limit["subsetnumberA"]
                sub_b = limit["subsetnumberB"]
                sub_a, sub_b = sorted([sub_a, sub_b])
                support = 1.0 if limit["concordanceSupport"] else 0.0
                support *= final_concordance_weights[concordance]
                score += support
                support_table[(sub_a, sub_b)] += support
                support_table_cap[(sub_a, sub_b)] += 1
        for limit in support_table:
            score_c += support_table[limit] * (
                support_table_cap[limit] / len(concordance_weights)
            )

        spart.addSpartitionData(
            spartition,
            CSU=score,
            CSW=score / combinations,
            CSWC=score_c / combinations,
        )

        def check_conspecific() -> bool:
            for subset in spart.getSpartitionSubsets(spartition):
                subset_individuals = spart.getSubsetIndividuals(spartition, subset)
                for group_individuals in conspecific_constraints:
                    for individual in group_individuals:
                        if individual not in subset_individuals:
                            continue
                        for other in group_individuals:
                            if other == individual:
                                continue
                            if other not in subset_individuals:
                                return False
            return True

        def check_heterospecific() -> bool:
            for subset in spart.getSpartitionSubsets(spartition):
                subset_individuals = spart.getSubsetIndividuals(spartition, subset)
                for group_individuals in heterospecific_constraints:
                    for individual in group_individuals:
                        if individual not in subset_individuals:
                            continue
                        for other in group_individuals:
                            if other == individual:
                                continue
                            if other in subset_individuals:
                                return False
            return True

        spart.addSpartitionData(spartition, CC="True" if check_conspecific() else "No")
        spart.addSpartitionData(
            spartition, HC="True" if check_heterospecific() else "No"
        )

    spart.toXML(output_path)

    tf = perf_counter()

    return Results(output_path, tf - ts)
