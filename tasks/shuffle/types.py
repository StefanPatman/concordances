from __future__ import annotations

from typing import NamedTuple


class PartitionInfo(NamedTuple):
    label: str
    subsets: int
    individuals: int


class OpenResults(NamedTuple):
    total_individuals: int
    partitions: list[PartitionInfo]
