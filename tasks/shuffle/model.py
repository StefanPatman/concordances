from PySide6 import QtCore

from pathlib import Path

from itaxotools.common.bindings import Property, Instance
from itaxotools.taxi_gui.model.tasks import SubtaskModel
from itaxotools.taxi_gui.threading import ReportDone

from . import process, title
from .types import PartitionInfo
from ..common.model import BlastTaskModel


class OpenSubtaskModel(SubtaskModel):
    task_name = "OpenSubtask"

    done = QtCore.Signal(object)

    def onDone(self, report: ReportDone):
        self.done.emit(report)
        self.busy = False


class PartitionTableModel(QtCore.QAbstractTableModel):
    checked_changed = QtCore.Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.headers = ["Partition", "Subsets", "Individuals"]
        self.rows: list[PartitionInfo] = []
        self.checked: dict[str, bool] = {}

    def rowCount(self, parent=QtCore.QModelIndex()):
        return len(self.rows)

    def columnCount(self, parent=QtCore.QModelIndex()):
        return len(self.headers)

    def data(self, index, role=QtCore.Qt.DisplayRole):
        if not index.isValid():
            return None

        row = self.rows[index.row()]
        col = index.column()

        if role == QtCore.Qt.DisplayRole:
            if col == 0:
                return row.label
            if col == 1:
                return row.subsets
            if col == 2:
                return row.individuals

        if role == QtCore.Qt.CheckStateRole and col == 0:
            if self.checked.get(row.label, False):
                return QtCore.Qt.Checked
            return QtCore.Qt.Unchecked

        if role == QtCore.Qt.TextAlignmentRole and col in (1, 2):
            return int(QtCore.Qt.AlignCenter)

        return None

    def flags(self, index):
        if not index.isValid():
            return QtCore.Qt.NoItemFlags

        flags = QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEnabled
        if index.column() == 0:
            flags |= QtCore.Qt.ItemIsUserCheckable
        return flags

    def setData(self, index, value, role=QtCore.Qt.EditRole):
        if not index.isValid():
            return False

        row = self.rows[index.row()]

        if index.column() == 0 and role == QtCore.Qt.CheckStateRole:
            state = QtCore.Qt.CheckState(value)
            self.checked[row.label] = bool(state == QtCore.Qt.Checked)
            self.dataChanged.emit(index, index, [QtCore.Qt.CheckStateRole])
            self.checked_changed.emit()
            return True

        return False

    def headerData(self, section, orientation, role=QtCore.Qt.DisplayRole):
        if role == QtCore.Qt.DisplayRole and orientation == QtCore.Qt.Horizontal:
            return self.headers[section]
        return None

    def set_partitions(self, partitions: list[PartitionInfo]):
        self.beginResetModel()
        self.rows = list(partitions)
        self.checked = {partition.label: True for partition in partitions}
        self.endResetModel()
        self.checked_changed.emit()

    def set_all_checked(self, checked: bool):
        if not self.rows:
            return
        for partition in self.rows:
            self.checked[partition.label] = checked
        top_left = self.index(0, 0)
        bottom_right = self.index(len(self.rows) - 1, 0)
        self.dataChanged.emit(top_left, bottom_right, [QtCore.Qt.CheckStateRole])
        self.checked_changed.emit()

    def clear(self):
        if not self.rows:
            return
        self.beginResetModel()
        self.rows = []
        self.checked = {}
        self.endResetModel()
        self.checked_changed.emit()

    def get_checked(self) -> list[str]:
        return [
            partition.label
            for partition in self.rows
            if self.checked.get(partition.label, False)
        ]


class Model(BlastTaskModel):
    task_name = title

    input_path = Property(Path, Path())
    output_path = Property(Path, Path())

    partitions = Property(PartitionTableModel, Instance)
    total_individuals = Property(int, 0)

    add_partitions = Property(int, 0)
    merge_count = Property(int, 0)
    split_count = Property(int, 0)
    swap_count = Property(int, 0)
    spread = Property(float, 0.6)

    def __init__(self, name=None):
        super().__init__(name)
        self.can_open = True
        self.can_save = False

        self.subtask_init = SubtaskModel(self, bind_busy=False)

        self.subtask_open = OpenSubtaskModel(self, bind_busy=True)
        self.binder.bind(self.subtask_open.done, self._handle_open_results)

        for handle in [
            self.properties.input_path,
            self.properties.output_path,
        ]:
            self.binder.bind(handle, self.checkReady)
        self.binder.bind(self.partitions.checked_changed, self.checkReady)
        self.checkReady()

        self.subtask_init.start(process.initialize)

    def _handle_open_results(self, report: ReportDone):
        results = report.result
        self.total_individuals = results.total_individuals
        self.partitions.set_partitions(results.partitions)

    def isReady(self):
        if self.input_path == Path():
            return False
        if self.output_path == Path():
            return False
        if not self.partitions.get_checked():
            return False
        return True

    def start(self):
        super().start()

        self.exec(
            process.execute,
            input_path=self.input_path,
            output_path=self.output_path,
            selected_partitions=self.partitions.get_checked(),
            add_partitions=self.add_partitions,
            merge_count=self.merge_count,
            split_count=self.split_count,
            swap_count=self.swap_count,
            spread=self.spread,
        )

    def onDone(self, report: ReportDone):
        self.report_results.emit(self.task_name, report.result)
        self.busy = False

    def open(self, path: Path):
        self.input_path = path
        if not path.is_file():
            self.output_path = Path()
            self.partitions.clear()
            return
        self.output_path = path.with_stem(path.stem + "_reshuffled")
        self.subtask_open.start(process.open_spart, path)
