from __future__ import annotations

from pathlib import Path
from typing import NamedTuple


class Results(NamedTuple):
    output_path: Path
    seconds_taken: float


class ScanResults(NamedTuple):
    pass
