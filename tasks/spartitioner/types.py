from __future__ import annotations

from pathlib import Path
from typing import NamedTuple

# Drag payload: a JSON list of individual names.
MIME_INDIVIDUALS = "application/x-spartitioner-individuals"

# Parts of a SPART file that are carried along untouched.
EXTRA_KEYS = [
    "project_name",
    "date",
    "individuals",
    "locations",
    "location_synonyms",
]


class SubsetData(NamedTuple):
    label: str
    individuals: list[str]


class SpartitionData(NamedTuple):
    """`original` is the spartition as it was read from file, or None for
    spartitions created in the editor. It holds the scores and concordances,
    which only still apply if the spartition is not `dirty`.
    """

    label: str
    subsets: list[SubsetData]
    original: dict | None
    dirty: bool


class DocumentData(NamedTuple):
    individuals: list[str]
    spartitions: list[SpartitionData]
    extras: dict


class SaveResults(NamedTuple):
    output_path: Path
    spartition_count: int
    seconds_taken: float
