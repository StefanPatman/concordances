from __future__ import annotations

from pathlib import Path
from typing import NamedTuple

# The arrow points the way the spartition columns are ordered.
SORT_ARROW_ASCENDING = "\u25b6"
SORT_ARROW_DESCENDING = "\u25c0"


class ScoreColumn(NamedTuple):
    """One sortable column of the review table.

    `key` is the SPART spartition data key, or None for values derived from the
    spartition structure itself, which cannot be dropped on export.
    """

    name: str
    key: str | None
    kind: str


SCORE_COLUMNS = [
    ScoreColumn("Nind", None, "int"),
    ScoreColumn("Nsub", None, "int"),
    ScoreColumn("Ncomp", None, "int"),
    ScoreColumn("asap", "spartitionScore", "float"),
    ScoreColumn("CSWm", "CSWm", "float"),
    ScoreColumn("BayesLog", "BayesLogFactor", "float"),
    ScoreColumn("BayesMean", "BayesMean", "float"),
    ScoreColumn("BayesMeanC", "BayesMeanC", "float"),
    ScoreColumn("BayesMeanCC", "BayesMeanCC", "float"),
    ScoreColumn("BayesMin", "BayesMin", "float"),
    ScoreColumn("BayesPP", "BayesPP", "float"),
    ScoreColumn("BIC", "BIC", "float"),
    ScoreColumn("AIC", "AIC", "float"),
    ScoreColumn("CSU", "CSU", "float"),
    ScoreColumn("CSW", "CSW", "float"),
    ScoreColumn("CSWC", "CSWC", "float"),
]

# Keys that describe the spartition itself, always kept when exporting.
STRUCTURAL_KEYS = {"label", "remarks", "subsets", "concordances"}


class Results(NamedTuple):
    individual_list: list[str]
    subset_table: dict[str, dict[str, str]]
    score_table: dict[str, dict[str, float | bool | None]]
    seconds_taken: float


class ExportResults(NamedTuple):
    output_path: Path
    spartition_count: int
    seconds_taken: float
