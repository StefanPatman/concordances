from itaxotools.spart_parser import Spart
from itaxotools.taxi2.sequences import Sequences, SequenceHandler
from itaxotools.taxi2.handlers import FileHandler
from itaxotools.taxi2.files import is_tabfile
from itaxotools.haplostats import HaploStats
from shapely import Polygon, MultiPoint
from geopy.distance import distance
from itertools import combinations, product
from collections import defaultdict
from pathlib import Path
from scipy.stats import mannwhitneyu
import math


def convex_hull(individuals: list[str], latlons: dict[str, tuple[float, float]]) -> Polygon:
    multipoint = MultiPoint([latlons[individual] for individual in individuals if individual in latlons])
    return multipoint.convex_hull


def read_latlons_from_spart(path: Path) -> dict[str, tuple[float, float]]:
    spart = Spart.fromXML(path)
    latlons = {individual: spart.getIndividualLatLon(individual) for individual in spart.getIndividuals()}
    latlons = {k: v for k, v in latlons.items() if v is not None}
    return latlons


def read_latlons_from_tabfile(path: Path) -> dict[str, tuple[float, float]]:
    with FileHandler.Tabfile(path, has_headers=True, get_all_columns=True) as file:
        return {id: (lat, lon) for id, lat, lon in file}


def process_polygons(spart: Spart, latlons: dict[str, tuple[float, float]]):
    for spartition in spart.getSpartitions():
        hulls = {}
        numbers = {}

        for subset in spart.getSpartitionSubsets(spartition):
            individuals = spart.getSubsetIndividuals(spartition, subset)
            hulls[subset] = convex_hull(individuals, latlons)
            numbers[subset] = len(individuals)

        kwargs = dict(
            evidenceType="Geography",
            evidenceDataType="Continuous",
            evidenceDiscriminationType="Overlap",
            evidenceDiscriminationDataType="Continuous",
        )
        spart.addConcordance(spartition, "polygon overlap area", **kwargs)

        kwargs = dict(
            evidenceType="Geography",
            evidenceDataType="Continuous",
            evidenceDiscriminationType="Boolean",
            evidenceDiscriminationDataType="Boolean",
        )
        spart.addConcordance(spartition, "polygon overlap bool", **kwargs)

        for subset_a, subset_b in combinations(hulls.keys(), 2):
            hull_a = hulls[subset_a]
            hull_b = hulls[subset_b]
            overlap = hull_a.intersection(hull_b)
            area = overlap.area

            if area:
                spart.addConcordantLimit(
                    spartitionLabel=spartition,
                    concordanceLabel="polygon overlap area",
                    subsetnumberA=subset_a,
                    subsetnumberB=subset_b,
                    NIndividualsSubsetA=numbers[subset_a],
                    NIndividualsSubsetB=numbers[subset_b],
                    concordanceSupport=float(area),
                )

            spart.addConcordantLimit(
                spartitionLabel=spartition,
                concordanceLabel="polygon overlap bool",
                subsetnumberA=subset_a,
                subsetnumberB=subset_b,
                NIndividualsSubsetA=numbers[subset_a],
                NIndividualsSubsetB=numbers[subset_b],
                concordanceSupport=bool(area),
            )


def process_coocurrences(spart: Spart, latlons: dict[str, tuple[float, float]], threshold_kilometers: float):
    for spartition in spart.getSpartitions():
        points = {}
        numbers = {}

        for subset in spart.getSpartitionSubsets(spartition):
            individuals = spart.getSubsetIndividuals(spartition, subset)
            points[subset] = [latlons[individual] for individual in individuals if individual in latlons]
            numbers[subset] = len(points)

        kwargs = dict(
            evidenceType="Geography",
            evidenceDataType="Continuous",
            evidenceDiscriminationType="Gap",
            evidenceDiscriminationDataType="Continuous",
            evidenceDiscriminationUnit="km",
        )
        spart.addConcordance(spartition, "co-occurence gap", **kwargs)

        kwargs = dict(
            evidenceType="Geography",
            evidenceDataType="Continuous",
            evidenceDiscriminationType="Gap",
            evidenceDiscriminationDataType="Boolean",
        )
        spart.addConcordance(spartition, "co-occurence boolean", **kwargs)

        for subset_a, subset_b in combinations(spart.getSpartitionSubsets(spartition), 2):
            points_a = points[subset_a]
            points_b = points[subset_b]

            min_distance = min(distance(a, b).km for a, b in product(points_a, points_b))

            spart.addConcordantLimit(
                spartitionLabel=spartition,
                concordanceLabel="co-occurence gap",
                subsetnumberA=subset_a,
                subsetnumberB=subset_b,
                NIndividualsSubsetA=numbers[subset_a],
                NIndividualsSubsetB=numbers[subset_b],
                concordanceSupport=min_distance,
            )

            spart.addConcordantLimit(
                spartitionLabel=spartition,
                concordanceLabel="co-occurence boolean",
                subsetnumberA=subset_a,
                subsetnumberB=subset_b,
                NIndividualsSubsetA=numbers[subset_a],
                NIndividualsSubsetB=numbers[subset_b],
                concordanceSupport=bool(min_distance <= threshold_kilometers),
            )


def is_id_allele_of_individual(id: str, individual: str) -> bool:
    if not id.startswith(individual):
        return False
    if len(id) != len(individual) + 2:
        return False
    return True


def process_haplostats(spart: Spart, sequences: Sequences):

    for spartition in spart.getSpartitions():
        stats = HaploStats()
        stats.set_subset_labels(
            subset_a="subset_a",
            subset_b="subset_b",
            subsets="subsets",
        )

        subset_sequences = defaultdict(list)
        numbers = {}

        for subset in spart.getSpartitionSubsets(spartition):
            individuals = spart.getSubsetIndividuals(spartition, subset)
            for individual in individuals:
                for sequence in sequences:
                    if is_id_allele_of_individual(sequence.id, individual):
                        subset_sequences[subset].append(sequence.seq)
            numbers[subset] = len(subset_sequences[subset])

        for subset, sequences in subset_sequences.items():
            if sequences:
                stats.add(subset, sequences)

        kwargs = dict(
            evidenceType="Molecular",
            evidenceDataType="Ordinal",
            evidenceDiscriminationType="Boolean",
            evidenceDiscriminationDataType="Boolean",
        )
        spart.addConcordance(spartition, "haplotypes shared between subsets", **kwargs)

        data = stats.get_haplotypes_shared_between_subsets(include_empty=True)
        for chunk in data:
            subset_a: str = chunk["subset_a"]
            subset_b: str = chunk["subset_b"]
            common: dict[str, int] = chunk["common"]
            spart.addConcordantLimit(
                spartitionLabel=spartition,
                concordanceLabel="haplotypes shared between subsets",
                subsetnumberA=subset_a,
                subsetnumberB=subset_b,
                NIndividualsSubsetA=numbers[subset_a],
                NIndividualsSubsetB=numbers[subset_b],
                concordanceSupport=bool(common),
            )

        kwargs = dict(
            evidenceType="Molecular",
            evidenceDataType="Ordinal",
            evidenceDiscriminationType="Boolean",
            evidenceDiscriminationDataType="Boolean",
        )
        spart.addConcordance(spartition, "FFRs shared between subsets", **kwargs)

        data = stats.get_fields_for_recombination_shared_between_subsets(include_empty=True)
        for chunk in data:
            subset_a: str = chunk["subset_a"]
            subset_b: str = chunk["subset_b"]
            common: dict[str, int] = chunk["common"]
            spart.addConcordantLimit(
                spartitionLabel=spartition,
                concordanceLabel="FFRs shared between subsets",
                subsetnumberA=subset_a,
                subsetnumberB=subset_b,
                NIndividualsSubsetA=numbers[subset_a],
                NIndividualsSubsetB=numbers[subset_b],
                concordanceSupport=bool(common),
            )


def read_morphometrics_from_tabfile(path: Path) -> dict[str, dict[str, float]]:
    data: dict[str, dict[str, float]] = defaultdict(dict)
    with FileHandler.Tabfile(path, has_headers=True, get_all_columns=True) as file:
        for row in file:
            id = row[0]
            for header, value in zip(file.headers[1:], row[1:]):
                data[header][id] = float(value)
    return data


def compute_range_gap(a: list[float], b: list[float]) -> float:
    """Returns negative value for overlap"""
    return max(min(a), min(b)) - min(max(a), max(b))


def process_morphometrics(spart: Spart, label: str, individual_data: dict[str, float]):

    for spartition in spart.getSpartitions():

        subset_data = defaultdict(list)
        numbers = {}

        for subset in spart.getSpartitionSubsets(spartition):
            individuals = spart.getSubsetIndividuals(spartition, subset)
            for individual in individuals:
                if individual in individual_data:
                    subset_data[subset].append(individual_data[individual])
            numbers[subset] = len(subset_data[subset])

        concordance_label_u = f"Mann-Whitney U-stat for {label}"
        concordance_label_p = f"Mann-Whitney P-value for {label}"
        concordance_label_b = f"Mann-Whitney P-value for {label} (Bonferroni corrected)"
        concordance_label_g = f"Measurement gap for {label}"

        kwargs = dict(
            evidenceType="Morphology",
            evidenceDataType="Continuous",
            evidenceDiscriminationType="Other",
            evidenceDiscriminationDataType="Continuous",
        )
        spart.addConcordance(spartition, concordance_label_u, **kwargs)

        kwargs = dict(
            evidenceType="Morphology",
            evidenceDataType="Continuous",
            evidenceDiscriminationType="Significance",
            evidenceDiscriminationDataType="Proportion",
        )
        spart.addConcordance(spartition, concordance_label_p, **kwargs)
        spart.addConcordance(spartition, concordance_label_b, **kwargs)

        kwargs = dict(
            evidenceType="Morphology",
            evidenceDataType="Continuous",
            evidenceDiscriminationType="Gap",
            evidenceDiscriminationDataType="Continuous",
        )
        spart.addConcordance(spartition, concordance_label_g, **kwargs)

        k = math.comb(len(subset_data), 2)

        for subset_a, subset_b in combinations(subset_data.keys(), 2):

            if len(subset_data[subset_a]) < 2:
                continue
            if len(subset_data[subset_b]) < 2:
                continue

            u, p = mannwhitneyu(subset_data[subset_a], subset_data[subset_b], alternative="two-sided")
            g = compute_range_gap(subset_data[subset_a], subset_data[subset_b])

            spart.addConcordantLimit(
                spartitionLabel=spartition,
                concordanceLabel=concordance_label_u,
                subsetnumberA=subset_a,
                subsetnumberB=subset_b,
                NIndividualsSubsetA=numbers[subset_a],
                NIndividualsSubsetB=numbers[subset_b],
                concordanceSupport=u,
            )
            spart.addConcordantLimit(
                spartitionLabel=spartition,
                concordanceLabel=concordance_label_p,
                subsetnumberA=subset_a,
                subsetnumberB=subset_b,
                NIndividualsSubsetA=numbers[subset_a],
                NIndividualsSubsetB=numbers[subset_b],
                concordanceSupport=p,
            )
            spart.addConcordantLimit(
                spartitionLabel=spartition,
                concordanceLabel=concordance_label_b,
                subsetnumberA=subset_a,
                subsetnumberB=subset_b,
                NIndividualsSubsetA=numbers[subset_a],
                NIndividualsSubsetB=numbers[subset_b],
                concordanceSupport=p * k,
            )
            spart.addConcordantLimit(
                spartitionLabel=spartition,
                concordanceLabel=concordance_label_g,
                subsetnumberA=subset_a,
                subsetnumberB=subset_b,
                NIndividualsSubsetA=numbers[subset_a],
                NIndividualsSubsetB=numbers[subset_b],
                concordanceSupport=g,
            )



def process_morphometrics_multiple(spart: Spart, data: dict[str, dict]):
    for header in data:
        process_morphometrics(spart, header, data[header])


def main():
    spart = Spart.fromXML("sample.xml")
    sequences = Sequences.fromPath("sample_sequences.fas", SequenceHandler.Fasta)
    # latlons = read_latlons_from_spart("sample.xml")
    latlons = read_latlons_from_tabfile("sample_latlons.tab")
    morphometrics = read_morphometrics_from_tabfile("sample_morphometrics.tab")
    process_polygons(spart, latlons)
    process_coocurrences(spart, latlons, 5.0)
    process_haplostats(spart, sequences)
    process_morphometrics_multiple(spart, morphometrics)
    spart.toXML("out.xml")


if __name__ == "__main__":
    main()
