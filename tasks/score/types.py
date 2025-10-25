from __future__ import annotations

from pathlib import Path
from typing import NamedTuple


class Results(NamedTuple):
    output_path: Path
    seconds_taken: float


class OpenResults(NamedTuple):
    spartition_data: dict[str, list[str]]
    concordance_data: dict[str, dict[str]]
