from __future__ import annotations

from typing import NamedTuple


class Results(NamedTuple):
    table: dict[str, dict[str, int]]
    seconds_taken: float
