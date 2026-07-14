import random
from pathlib import Path
from time import perf_counter

from ..common.types import Results
from .types import OpenResults, PartitionInfo

# Spread of the sampling bell relative to its mean. Higher = more variation
# between partitions (occasional large values); lower = flatter, more uniform.
BELL_SIGMA = 0.6


def sample_bell(
    count: int, total: int, rng: random.Random, sigma: float = BELL_SIGMA
) -> list[int]:
    """Sample a bell curve `count` times and scale it to sum to exactly `total`.

    Each of the `count` new partitions draws one sample from a bell centered at
    1 with spread `sigma`, so partitions vary around the mean with the odd
    larger value. The samples are normalized so their float sum equals `total`,
    floored to integers, and the leftover units are handed to the largest
    fractional parts so the integer counts sum to exactly `total`.
    """
    if count <= 0:
        return []
    if total <= 0:
        return [0] * count

    samples = [max(0.0, rng.gauss(1.0, sigma)) for _ in range(count)]
    weight = sum(samples)
    if weight > 0:
        raw = [sample * total / weight for sample in samples]
    else:
        # Every sample clamped to zero: fall back to an even spread.
        raw = [total / count] * count

    counts = [int(value) for value in raw]
    remainder = total - sum(counts)
    order = sorted(range(count), key=lambda i: raw[i] - counts[i], reverse=True)
    for i in range(remainder):
        counts[order[i]] += 1

    return counts


def fill_empty_partitions(op_samples: dict[str, list[int]], count: int) -> None:
    """Ensure no partition is left a plain copy (zero of every operation).

    Any partition with no operations takes a single unit from the partition
    that currently has the most, keeping each operation's total unchanged.
    Stops early if there are not enough operations to cover every partition.
    """
    names = list(op_samples)

    def total_at(index: int) -> int:
        return sum(op_samples[name][index] for name in names)

    for index in range(count):
        if total_at(index) > 0:
            continue

        donor = max(range(count), key=total_at)
        if total_at(donor) < 2:
            break

        name = max(names, key=lambda n: op_samples[n][donor])
        op_samples[name][donor] -= 1
        op_samples[name][index] += 1


def plan_new_partitions(
    new_partitions: int,
    operation_totals: dict[str, int],
    rng: random.Random,
    sigma: float = BELL_SIGMA,
) -> tuple[dict[str, list[int]], list[dict[str, int]]]:
    """Plan how many of each operation is applied to each new partition.

    Each active operation is one axis of an N-dimensional bell (N is the number
    of active operations). We draw one point per new partition, so every
    operation gets `new_partitions` samples, each normalized to its total.
    """
    recipes: list[dict[str, int]] = [dict() for _ in range(new_partitions)]

    active = {name: total for name, total in operation_totals.items() if total > 0}
    if new_partitions <= 0 or not active:
        return {}, recipes

    op_samples = {
        name: sample_bell(new_partitions, total, rng, sigma)
        for name, total in active.items()
    }
    fill_empty_partitions(op_samples, new_partitions)

    for name, samples in op_samples.items():
        for index, value in enumerate(samples):
            if value > 0:
                recipes[index][name] = value

    return op_samples, recipes


def initialize():
    import itaxotools

    itaxotools.progress_handler("Initializing...")
    import core  # noqa
    import itaxotools.spart_parser  # noqa


def open_spart(path: Path) -> OpenResults:
    from itaxotools.spart_parser import Spart

    if not path.is_file():
        return OpenResults(0, [])

    spart = Spart.fromXML(path)

    total_individuals = len(spart.getIndividuals())

    partitions: list[PartitionInfo] = []
    for spartition in spart.getSpartitions():
        subsets = spart.getSpartitionSubsets(spartition)
        individual_count = sum(
            len(spart.getSubsetIndividuals(spartition, subset)) for subset in subsets
        )
        partitions.append(PartitionInfo(spartition, len(subsets), individual_count))

    return OpenResults(total_individuals, partitions)


def execute(
    input_path: Path,
    output_path: Path,
    selected_partitions: list[str],
    add_partitions: int,
    merge_count: int,
    split_count: int,
    swap_count: int,
    spread: float,
) -> Results:
    from itaxotools.spart_parser import Spart

    ts = perf_counter()

    rng = random.Random()

    spart = Spart.fromXML(input_path)
    spartitions = spart.getSpartitions()

    print(f"Spart file: {input_path.name}")
    print(f"Selected partitions: {len(selected_partitions)}")
    print()

    for spartition in spartitions:
        if spartition not in selected_partitions:
            continue

        print(f"Partition '{spartition}':")

        if add_partitions <= 0:
            continue

        operation_totals = {
            "split": split_count,
            "merge": merge_count,
            "swap": swap_count,
        }
        op_samples, recipes = plan_new_partitions(
            add_partitions, operation_totals, rng, spread
        )

        for name, samples in op_samples.items():
            print(
                f"  {name}: {samples} (target {operation_totals[name]}, sum {sum(samples)})"
            )
        print(f"  New partitions ({len(recipes)}):")
        for index, recipe in enumerate(recipes, start=1):
            if recipe:
                summary = ", ".join(f"{name}={count}" for name, count in recipe.items())
            else:
                summary = "copy (no operations)"
            print(f"    {index}: {summary}")

    # TODO: apply each recipe to generate the new partitions, then write the
    # result to output_path.

    tf = perf_counter()

    return Results(output_path, tf - ts)
