from __future__ import annotations

from pathlib import Path
from typing import NamedTuple


class Results(NamedTuple):
    output_path: Path
    seconds_taken: float


class OpenResults(NamedTuple):
    concordance_data: dict[str, dict[str]]
    individuals_list: list[str]
