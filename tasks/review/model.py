from PySide6 import QtCore, QtGui

from pathlib import Path

from itaxotools.common.bindings import Instance, Property
from itaxotools.taxi_gui.model.tasks import SubtaskModel
from itaxotools.taxi_gui.threading import ReportDone
from itaxotools.taxi_gui.types import Notification

from . import process, title
from ..common.model import BlastTaskModel
from ..common.types import column_label
from .types import (
    SCORE_COLUMNS,
    SORT_ARROW_ASCENDING,
    SORT_ARROW_DESCENDING,
    ExportResults,
)


class ExportSubtaskModel(SubtaskModel):
    task_name = "ExportSubtask"

    done = QtCore.Signal(object)

    def onDone(self, report: ReportDone):
        self.done.emit(report)
        self.busy = False


class SpartitionTableModel(QtCore.QAbstractTableModel):
    """Spartitions are columns and scores are rows, as in the Visualize task.

    Qt only ever sorts rows, so the spartition order cannot come from a sort
    proxy. It is kept here in `order` and rebuilt on demand, which also makes
    it the single source of truth for the export order.

    Columns are headed by a short letter rather than the full spartition name,
    which would be far too wide. The letter is assigned in file order and
    travels with its spartition through sorting, so it stays a stable handle
    and matches the letter the Visualize task gives the same spartition.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        # A copy: rows are removable, and SCORE_COLUMNS is shared module state.
        self.score_rows = list(SCORE_COLUMNS)
        self.order: list[str] = []
        self.labels: dict[str, str] = {}
        self.scores: dict[str, dict[str, float | bool | None]] = {}
        self.sort_row: int | None = None
        self.sort_by_name = False
        self.sort_ascending = True

    def rowCount(self, parent=QtCore.QModelIndex()):
        return len(self.score_rows)

    def columnCount(self, parent=QtCore.QModelIndex()):
        return len(self.order)

    @staticmethod
    def format_value(value: float | bool | None) -> str:
        if value is None:
            return "-"
        if isinstance(value, bool):
            return "\u2713" if value else "\u2717"
        if isinstance(value, int):
            return str(value)
        if isinstance(value, float):
            return f"{value:.3f}"
        return str(value)

    @staticmethod
    def sort_key(value: float | bool) -> float:
        return float(value)

    def data(self, index, role=QtCore.Qt.DisplayRole):
        if not index.isValid():
            return None

        spartition = self.order[index.column()]
        column = self.score_rows[index.row()]
        value = self.scores[spartition].get(column.name, None)

        if role == QtCore.Qt.UserRole:
            return value
        if role == QtCore.Qt.DisplayRole:
            return self.format_value(value)
        if role == QtCore.Qt.TextAlignmentRole:
            return QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter
        if role == QtCore.Qt.ToolTipRole:
            return f"{spartition}\n{column.name}: {self.format_value(value)}"

        return None

    def headerData(self, section, orientation, role=QtCore.Qt.DisplayRole):
        if orientation == QtCore.Qt.Horizontal:
            if not 0 <= section < len(self.order):
                return None
            spartition = self.order[section]
            if role == QtCore.Qt.DisplayRole:
                return self.labels[spartition]
            if role == QtCore.Qt.ToolTipRole:
                return spartition
            if role == QtCore.Qt.TextAlignmentRole:
                return QtCore.Qt.AlignCenter
            return None

        if not 0 <= section < len(self.score_rows):
            return None
        column = self.score_rows[section]
        sorted_by_this = self.sort_row == section and not self.sort_by_name

        if role == QtCore.Qt.DisplayRole:
            # Qt's own sort indicator eats the label on a vertical header, so
            # the arrow is part of the text instead. It points the way the
            # spartition columns are ordered.
            if sorted_by_this:
                if self.sort_ascending:
                    return f"{column.name} {SORT_ARROW_ASCENDING}"
                return f"{column.name} {SORT_ARROW_DESCENDING}"
            return column.name
        if role == QtCore.Qt.FontRole:
            if sorted_by_this:
                font = QtGui.QFont()
                font.setBold(True)
                return font
            return None
        if role == QtCore.Qt.ToolTipRole:
            if column.key is None:
                return f"{column.name} (derived from the spartition)"
            return f"{column.name} ({column.key})"

        return None

    def set_data(self, score_table: dict[str, dict[str, float | bool | None]]):
        self.beginResetModel()
        self.score_rows = list(SCORE_COLUMNS)
        self.order = list(score_table)
        self.labels = {
            spartition: column_label(index)
            for index, spartition in enumerate(self.order)
        }
        self.scores = score_table
        self.sort_row = None
        self.sort_by_name = False
        self.sort_ascending = True
        self.endResetModel()

    def clear(self):
        self.beginResetModel()
        self.order = []
        self.labels = {}
        self.scores = {}
        self.sort_row = None
        self.sort_by_name = False
        self.endResetModel()

    def sort_by_score(self, section: int):
        """Order the spartition columns by the given score row."""
        if not self.order:
            return
        if self.sort_row == section and not self.sort_by_name:
            self.sort_ascending = not self.sort_ascending
        else:
            self.sort_row = section
            self.sort_by_name = False
            self.sort_ascending = True
        self.reorder()

    def sort_by_spartition_name(self):
        if not self.order:
            return
        if self.sort_by_name:
            self.sort_ascending = not self.sort_ascending
        else:
            self.sort_by_name = True
            self.sort_row = None
            self.sort_ascending = True
        self.reorder()

    def reorder(self):
        if self.sort_by_name:
            order = sorted(
                self.order, key=str.casefold, reverse=not self.sort_ascending
            )
        elif self.sort_row is not None:
            name = self.score_rows[self.sort_row].name
            present = [s for s in self.order if self.scores[s].get(name) is not None]
            missing = [s for s in self.order if self.scores[s].get(name) is None]
            present.sort(
                key=lambda s: self.sort_key(self.scores[s][name]),
                reverse=not self.sort_ascending,
            )
            # Spartitions missing the score stay at the end either way.
            order = present + missing
        else:
            return

        self.beginResetModel()
        self.order = order
        self.endResetModel()

    def remove_columns(self, columns: list[int]):
        """Drop the given spartition columns from the view, not from the file."""
        chosen = {self.order[c] for c in columns if 0 <= c < len(self.order)}
        if not chosen:
            return
        self.beginResetModel()
        self.order = [s for s in self.order if s not in chosen]
        self.endResetModel()

    def remove_rows(self, rows: list[int]):
        """Drop the given score rows from the view, not from the file."""
        chosen = {
            self.score_rows[r].name for r in rows if 0 <= r < len(self.score_rows)
        }
        if not chosen:
            return

        sorted_name = None
        if self.sort_row is not None:
            sorted_name = self.score_rows[self.sort_row].name

        self.beginResetModel()
        self.score_rows = [c for c in self.score_rows if c.name not in chosen]
        # The sorted row may have shifted, or gone away with the selection.
        if sorted_name is None or sorted_name in chosen:
            self.sort_row = None
        else:
            names = [c.name for c in self.score_rows]
            self.sort_row = names.index(sorted_name)
        self.endResetModel()

    def get_spartitions(self) -> list[str]:
        """Every spartition still shown, in the order the table shows them."""
        return list(self.order)

    def get_keys(self) -> list[str]:
        """The SPART keys of every score row still shown."""
        return [c.key for c in self.score_rows if c.key is not None]


class Model(BlastTaskModel):
    task_name = title

    report_saved = QtCore.Signal(object)

    concordance_path = Property(Path, Path())
    individual_list = Property(list, [])
    subset_table = Property(dict, {})
    spartitions = Property(SpartitionTableModel, Instance)

    def __init__(self, name=None):
        super().__init__(name)
        self.can_open = True
        self.can_save = True
        self.show_save = True
        self.can_start = False

        self.subtask_init = SubtaskModel(self, bind_busy=False)
        self.subtask_init.start(process.initialize)

        self.subtask_export = ExportSubtaskModel(self, bind_busy=True)
        self.binder.bind(self.subtask_export.done, self._handle_export_done)

    def isReady(self):
        return True

    def start(self):
        super().start()

        self.exec(
            process.execute,
            concordance_path=self.concordance_path,
        )

    def onDone(self, report: ReportDone):
        self.individual_list = report.result.individual_list
        self.subset_table = report.result.subset_table
        self.spartitions.set_data(report.result.score_table)
        self.report_results.emit(self.task_name, report.result)
        self.busy = False
        self.done = True

    def open(self, path: Path):
        self.concordance_path = path
        self.start()

    def clear(self):
        """Restore the table by reading the file again."""
        super().clear()
        if self.concordance_path == Path():
            self.spartitions.clear()
            self.individual_list = []
            self.subset_table = {}
            return
        self.start()

    def save_selection(self, path: Path, spartitions: list[str], keys: list[str]):
        if not spartitions:
            self.notification.emit(
                Notification.Warn("There are no spartitions left to save.")
            )
            return

        self.subtask_export.start(
            process.export,
            self.concordance_path,
            path,
            spartitions,
            keys,
        )

    def _handle_export_done(self, report: ReportDone):
        results: ExportResults = report.result
        self.report_saved.emit(results)
