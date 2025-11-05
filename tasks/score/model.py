from PySide6 import QtCore
from pathlib import Path
from collections import defaultdict

from itaxotools.common.bindings import Property, Instance
from itaxotools.taxi_gui.model.tasks import SubtaskModel
from itaxotools.taxi_gui.threading import ReportDone
from itaxotools.taxi_gui.types import Notification
from . import process, title
from ..common.model import BlastTaskModel
from .types import OpenResults


class VersionSubtaskModel(SubtaskModel):
    task_name = "OpenSubtask"

    done = QtCore.Signal(OpenResults)

    def onDone(self, results: OpenResults):
        self.done.emit(results)
        self.busy = False


class ConcordanceTableModel(QtCore.QAbstractTableModel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.headers = [
            "Evidence name",
            "Evidence type",
            "Data type",
            "Discr. type",
            "Discr. data type",
            "Weight",
        ]
        self.keys = [
            "evidenceName",
            "evidenceType",
            "evidenceDataType",
            "evidenceDiscriminationType",
            "evidenceDiscriminationDataType",
        ]
        self.ids: dict[str, int] = {}
        self.checked: dict[str, bool] = {}
        self.weights: dict[str, float] = {}

        self.rows: list[dict] = []

    def rowCount(self, parent=QtCore.QModelIndex()):
        return len(self.rows)

    def columnCount(self, parent=QtCore.QModelIndex()):
        return len(self.headers)

    def data(self, index, role=QtCore.Qt.DisplayRole):
        if not index.isValid():
            return None

        row = self.rows[index.row()]
        col = index.column()
        id = row.get("evidenceName", None)

        if role == QtCore.Qt.DisplayRole:
            if col < 5:
                return row.get(self.keys[col], "")
            if col == 5:
                return f"{self.weights[id]:.2f}"

        if role == QtCore.Qt.CheckStateRole:
            if col == 0:
                if self.checked[id]:
                    return QtCore.Qt.Checked
                else:
                    return QtCore.Qt.Unchecked
            return None

        if role == QtCore.Qt.EditRole:
            if col == 5:
                return self.weights[id]
            return None

        return None

    def flags(self, index):
        if not index.isValid():
            return QtCore.Qt.NoItemFlags

        col = index.column()
        flags = QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEnabled

        if col == 0:
            flags |= QtCore.Qt.ItemIsUserCheckable
        elif col == 5:
            flags |= QtCore.Qt.ItemIsEditable

        return flags

    def setData(self, index, value, role=QtCore.Qt.EditRole):
        if not index.isValid():
            return False

        row = self.rows[index.row()]
        col = index.column()
        id = row.get("evidenceName", None)

        if col == 0 and role == QtCore.Qt.CheckStateRole:
            state = QtCore.Qt.CheckState(value)
            self.checked[id] = bool(state == QtCore.Qt.Checked)
            self.dataChanged.emit(index, index, [QtCore.Qt.CheckStateRole])
            return True

        elif col == 5 and role == QtCore.Qt.EditRole:
            try:
                self.weights[id] = float(value)
                self.dataChanged.emit(index, index, [QtCore.Qt.DisplayRole])
                return True
            except ValueError:
                return False

        return False

    def headerData(self, section, orientation, role=QtCore.Qt.DisplayRole):
        if role == QtCore.Qt.DisplayRole and orientation == QtCore.Qt.Horizontal:
            return self.headers[section]
        return None

    def clear(self):
        if not self.rows:
            return
        self.beginRemoveRows(QtCore.QModelIndex(), 0, len(self.rows) - 1)
        self.rows.clear()
        self.checked.clear()
        self.weights.clear()
        self.endRemoveRows()

    def insertRows(
        self,
        row_datas: list[dict[str, str]],
        checked_dict: dict[str, bool],
        weight_dict: dict[str, float],
    ):
        if not row_datas:
            return
        first = len(self.rows)
        last = first + len(row_datas) - 1
        self.beginInsertRows(QtCore.QModelIndex(), first, last)
        for i, (id, row_data) in enumerate(row_datas.items()):
            row_data["evidenceName"] = id
            self.rows.append(row_data)
            self.ids[id] = first + i
            self.checked[id] = checked_dict[id]
            self.weights[id] = weight_dict[id]
        self.endInsertRows()

    def get_weights(self) -> dict[str, float]:
        return {
            evidence_id: weight
            for evidence_id, weight in self.weights.items()
            if self.checked.get(evidence_id, False)
        }


class BooleanFilterProxyModel(QtCore.QSortFilterProxyModel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._show_boolean_only = False

    def filterAcceptsRow(self, source_row, source_parent):
        if not self._show_boolean_only:
            return True

        model = self.sourceModel()
        index = model.index(source_row, 0, source_parent)
        if not index.isValid():
            return False

        row_data = model.rows[source_row]
        dtype = row_data.get("evidenceDiscriminationDataType", "")
        return dtype == "Boolean"

    def flags(self, index):
        if not index.isValid():
            return QtCore.Qt.NoItemFlags

        src_index = self.mapToSource(index)
        model = self.sourceModel()
        row_data = model.rows[src_index.row()]

        base_flags = super().flags(index)

        if row_data.get("evidenceDiscriminationDataType", "") != "Boolean":
            base_flags &= ~QtCore.Qt.ItemIsEnabled
            base_flags &= ~QtCore.Qt.ItemIsEditable
            base_flags &= ~QtCore.Qt.ItemIsUserCheckable

        return base_flags

    def show_boolean_only(self, enabled: bool):
        self._show_boolean_only = enabled
        self.beginResetModel()
        self.invalidateFilter()
        self.endResetModel()


class IndividualListModel(QtCore.QAbstractListModel):
    def __init__(self, names=None):
        super().__init__()
        self.names = []
        self.names_set = set()
        self.set_names(names or [])

    def data(self, index, role):
        if role == QtCore.Qt.DisplayRole and index.isValid():
            return self.names[index.row()]

    def rowCount(self, parent=QtCore.QModelIndex()):
        return len(self.names)

    def set_names(self, names: list[str]):
        self.beginResetModel()
        self.names = names
        self.names_set = set(names)
        self.endResetModel()


class EvidenceTypeModel(QtCore.QAbstractTableModel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.headers = [
            "Evidence type",
            "Weight",
            "Member weighting behaviour",
        ]
        self.checked: dict[str, bool] = {}
        self.weights: dict[str, float] = {}

        self.rows: list[str] = []

    def rowCount(self, parent=QtCore.QModelIndex()):
        return len(self.rows)

    def columnCount(self, parent=QtCore.QModelIndex()):
        return len(self.headers)

    def data(self, index, role=QtCore.Qt.DisplayRole):
        if not index.isValid():
            return None

        dtype = self.rows[index.row()]
        col = index.column()

        if role == QtCore.Qt.DisplayRole:
            if col == 0:
                return dtype
            elif col == 1:
                return f"{self.weights[dtype]:.2f}"
            elif col == 2:
                return "Multiply by number of variables"

        if role == QtCore.Qt.CheckStateRole:
            if col == 2:
                if self.checked[dtype]:
                    return QtCore.Qt.Checked
                else:
                    return QtCore.Qt.Unchecked
            return None

        if role == QtCore.Qt.EditRole:
            if col == 1:
                return self.weights[dtype]
            return None

        return None

    def flags(self, index):
        if not index.isValid():
            return QtCore.Qt.NoItemFlags

        col = index.column()
        flags = QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEnabled

        if col == 1:
            flags |= QtCore.Qt.ItemIsEditable
        elif col == 2:
            flags |= QtCore.Qt.ItemIsUserCheckable

        return flags

    def setData(self, index, value, role=QtCore.Qt.EditRole):
        if not index.isValid():
            return False

        dtype = self.rows[index.row()]
        col = index.column()

        if col == 2 and role == QtCore.Qt.CheckStateRole:
            state = QtCore.Qt.CheckState(value)
            self.checked[dtype] = bool(state == QtCore.Qt.Checked)
            self.dataChanged.emit(index, index, [QtCore.Qt.CheckStateRole])
            return True

        elif col == 1 and role == QtCore.Qt.EditRole:
            try:
                self.weights[dtype] = float(value)
                self.dataChanged.emit(index, index, [QtCore.Qt.DisplayRole])
                return True
            except ValueError:
                return False

        return False

    def headerData(self, section, orientation, role=QtCore.Qt.DisplayRole):
        if role == QtCore.Qt.DisplayRole and orientation == QtCore.Qt.Horizontal:
            return self.headers[section]
        return None

    def clear(self):
        if not self.rows:
            return
        self.beginRemoveRows(QtCore.QModelIndex(), 0, len(self.rows) - 1)
        self.rows.clear()
        self.checked.clear()
        self.weights.clear()
        self.endRemoveRows()

    def insertRows(
        self,
        row_dtypes: list[str],
        checked_dict: dict[str, bool],
        weights_dict: dict[str, float],
    ):
        if not row_dtypes:
            return
        first = len(self.rows)
        last = first + len(row_dtypes) - 1
        self.beginInsertRows(QtCore.QModelIndex(), first, last)
        for i, dtype in enumerate(row_dtypes):
            self.rows.append(dtype)
            self.checked[dtype] = checked_dict[dtype]
            self.weights[dtype] = weights_dict[dtype]
        self.endInsertRows()

    def get_weights(self) -> dict[str, float]:
        return self.weights

    def get_behaviours(self) -> dict[str, bool]:
        return self.checked


class Model(BlastTaskModel):
    task_name = title

    concordance_path = Property(Path, Path())
    output_path = Property(Path, Path())

    individuals = Property(IndividualListModel, Instance)
    conspecific_constraints_text = Property(str, "")
    heterospecific_constraints_text = Property(str, "")
    conspecific_constraints_enabled = Property(bool, False)
    heterospecific_constraints_enabled = Property(bool, False)

    concordances = Property(ConcordanceTableModel, Instance)
    evidence_types = Property(EvidenceTypeModel, Instance)
    bool_only = Property(bool, True)

    def __init__(self, name=None):
        super().__init__(name)
        self.can_open = True
        self.can_save = False

        self.subtask_init = SubtaskModel(self, bind_busy=False)

        self.subtask_open = VersionSubtaskModel(self, bind_busy=True)
        self.binder.bind(self.subtask_open.done, self._handle_open_results)

        for handle in [
            self.properties.concordance_path,
            self.properties.output_path,
        ]:
            self.binder.bind(handle, self.checkReady)
        self.checkReady()

        self.subtask_init.start(process.initialize)

    def _handle_open_results(self, results: ReportDone):
        individuals_list = results.result.individuals_list
        self.individuals.set_names(individuals_list)

        concordance_data = results.result.concordance_data

        checked_dict = {
            id: bool(row_data["evidenceDiscriminationDataType"] == "Boolean")
            for id, row_data in concordance_data.items()
        }
        weights_dict = {
            id: 1.0 if checked else 0.0 for id, checked in checked_dict.items()
        }

        self.concordances.clear()
        self.concordances.insertRows(
            row_datas=concordance_data,
            checked_dict=checked_dict,
            weight_dict=weights_dict,
        )

        evidence_types_set = {
            row_data["evidenceType"] for row_data in concordance_data.values()
        }

        self.evidence_types.clear()
        self.evidence_types.insertRows(
            row_dtypes=list(sorted(evidence_types_set)),
            checked_dict=defaultdict(lambda: True),
            weights_dict=defaultdict(lambda: 1.0),
        )

    def isReady(self):
        if self.concordance_path == Path():
            return False
        if self.output_path == Path():
            return False
        return True

    def start(self):
        super().start()

        try:
            conspecific_constraints = self._parse_conspecific_constraints_list()
        except Exception as e:
            note = Notification.Fail("Conspecific constraints error: \n" + str(e))
            self.notification.emit(note)
            self.busy = False
            return

        try:
            heterospecific_constraints = self._parse_heterospecific_constraints_list()
        except Exception as e:
            note = Notification.Fail("Heterospecific constraint error: \n" + str(e))
            self.notification.emit(note)
            self.busy = False
            return

        self.exec(
            process.execute,
            concordance_path=self.concordance_path,
            output_path=self.output_path,
            concordance_weights=self.concordances.get_weights(),
            evidence_types_weights=self.evidence_types.get_weights(),
            evidence_types_behaviours=self.evidence_types.get_behaviours(),
            conspecific_constraints=conspecific_constraints,
            heterospecific_constraints=heterospecific_constraints,
        )

    def _parse_constraints_list(self, text: str) -> list[list[str]]:
        groups = []
        group = set()
        for line in str(text + "\n\n").splitlines():
            name = line.strip()
            if name:
                if name not in self.individuals.names_set:
                    raise Exception(f"Individual not found: {repr(name)}")
                if name in group:
                    raise Exception(
                        f"Individual appears twice in the same group: {repr(name)}"
                    )
                group.add(name)
            elif group:
                if len(group) < 2:
                    raise Exception("Groups must have at least two individuals")
                groups.append(list(group))
                group = []
        return groups

    def _parse_conspecific_constraints_list(self) -> list[list[str]]:
        if self.conspecific_constraints_enabled:
            return self._parse_constraints_list(self.conspecific_constraints_text)
        return []

    def _parse_heterospecific_constraints_list(self) -> list[list[str]]:
        if self.heterospecific_constraints_enabled:
            return self._parse_constraints_list(self.heterospecific_constraints_text)
        return []

    def onDone(self, report: ReportDone):
        self.report_results.emit(self.task_name, report.result)
        self.busy = False

    def open(self, path: Path):
        self.concordance_path = path
        if not path.is_file():
            self.output_path = Path()
            self.concordances.clear()
            return
        self.output_path = path.with_stem(path.stem + "_scored")
        self.subtask_open.start(process.open_spart, path)
