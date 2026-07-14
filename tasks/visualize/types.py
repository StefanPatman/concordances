from __future__ import annotations

from typing import NamedTuple


class Separator:
    """Marks a horizontal separator between score rows."""


class Results(NamedTuple):
    individual_list: list[str]
    subset_table: dict[str, dict[str, str]]
    score_table: dict[str, dict[str, float | bool]]
    seconds_taken: float
