from itaxotools.spart_parser import Spart
from shapely import Polygon, MultiPoint
from geopy.distance import distance
from itertools import combinations, product


def convex_hull(individuals: list[str], latlons: dict[str, tuple[float, float]]) -> Polygon:
    multipoint = MultiPoint([latlons[individual] for individual in individuals if individual in latlons])
    return multipoint.convex_hull


def process_polygons(spart: Spart):
    latlons = {individual: spart.getIndividualLatLon(individual) for individual in spart.getIndividuals()}
    latlons = {k: v for k, v in latlons.items() if v is not None}

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


def process_coocurrences(spart: Spart, threshold_kilometers: float):
    latlons = {individual: spart.getIndividualLatLon(individual) for individual in spart.getIndividuals()}
    latlons = {k: v for k, v in latlons.items() if v is not None}

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


def main():
    spart = Spart.fromXML("sample.xml")
    process_polygons(spart)
    process_coocurrences(spart, 5.0)
    spart.toXML("out.xml")


if __name__ == "__main__":
    main()
