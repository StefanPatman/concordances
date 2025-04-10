from itaxotools.spart_parser import Spart
from shapely import Polygon, MultiPoint
from itertools import combinations


def convex_hull(individuals: list[str], latlons: dict[str, tuple[float, float]]) -> Polygon:
    multipoint = MultiPoint([latlons[individual] for individual in individuals if individual in latlons])
    return multipoint.convex_hull


def main():
    spart = Spart.fromXML("sample.xml")

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

    spart.toXML("out.xml")

if __name__ == "__main__":
    main()
