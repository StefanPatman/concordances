from PySide6 import QtCore, QtWidgets

from pathlib import Path

from itaxotools.taxi_gui import app
from itaxotools.taxi_gui.utility import human_readable_seconds
from itaxotools.taxi_gui.view.tasks import TaskView

from ..visualize.model import Model as VisualizeModel
from ..visualize.view import Visualizer
from .types import ExportResults, Results


class ReviewTableView(QtWidgets.QTableView):
    """Spartitions across, scores down.

    Clicking a score name sorts the spartition columns by that score. Selection
    is left to Qt, and Delete prunes the selection from the view, so what the
    table shows is what gets saved.
    """

    spartitionActivated = QtCore.Signal(str)
    scoreClicked = QtCore.Signal(int)
    deleteRequested = QtCore.Signal()

    def __init__(self, parent=None):
        super().__init__(parent)

        self.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectItems)
        self.setSelectionMode(QtWidgets.QAbstractItemView.ExtendedSelection)
        self.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        self.setAlternatingRowColors(True)
        self.setWordWrap(False)

        header = self.verticalHeader()
        header.setSectionsClickable(True)
        header.sectionClicked.connect(self.scoreClicked)
        # Wide enough for the score names and the sort arrow beside them.
        header.setFixedWidth(160)
        header.setSectionResizeMode(QtWidgets.QHeaderView.Fixed)
        header.setDefaultSectionSize(36)

        self.horizontalHeader().setSectionsClickable(True)

        self.doubleClicked.connect(self._handle_double_clicked)

    def keyPressEvent(self, event):
        if event.key() in (QtCore.Qt.Key_Delete, QtCore.Qt.Key_Backspace):
            self.deleteRequested.emit()
            return
        super().keyPressEvent(event)

    def _handle_double_clicked(self, index):
        if not index.isValid():
            return
        name = index.model().headerData(
            index.column(), QtCore.Qt.Horizontal, QtCore.Qt.ToolTipRole
        )
        if name:
            self.spartitionActivated.emit(name)

    def get_selected_columns(self) -> list[int]:
        """Every column holding a selected cell, not just fully selected ones.

        Selecting any cell is enough to mean its spartition.
        """
        return sorted(
            {index.column() for index in self.selectionModel().selectedIndexes()}
        )

    def get_selected_rows(self) -> list[int]:
        """Only fully selected rows, since any cell already means its column."""
        return [index.row() for index in self.selectionModel().selectedRows()]


class PreviewDialog(QtWidgets.QDialog):
    """A single spartition drawn in the same style as the Visualize task."""

    def __init__(
        self,
        spartition: str,
        individual_list: list[str],
        subset: dict[str, str],
        scores: dict[str, float | bool | None],
        parent=None,
    ):
        super().__init__(parent)
        self.setWindowTitle(f"{app.config.title} - {spartition}")
        self.setWindowFlag(QtCore.Qt.Window)
        self.setAttribute(QtCore.Qt.WA_DeleteOnClose)
        self.resize(520, 720)

        visualizer = Visualizer(self)
        visualizer.set_data(individual_list, {spartition: subset}, {spartition: scores})

        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(visualizer, 1)
        layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(layout)


class View(TaskView):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.results: Results | None = None
        self.source_model = None
        self.previews = []

        self.draw()

    def draw(self):
        self.table = ReviewTableView(self)
        self.table.spartitionActivated.connect(self.show_preview)
        self.table.scoreClicked.connect(self.sort_by_score)
        self.table.deleteRequested.connect(self.remove_selection)

        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(self.table, 1)
        layout.setSpacing(6)
        layout.setContentsMargins(6, 6, 6, 6)

        self.setLayout(layout)

    def setObject(self, object):
        self.object = object
        self.binder.unbind_all()

        self.binder.bind(object.notification, self.showNotification)
        self.binder.bind(object.report_results, self.report_results)
        self.binder.bind(object.report_saved, self.report_saved)

        self.set_model(object.spartitions)

    def set_model(self, model):
        self.source_model = model
        self.table.setModel(model)

        # The corner button restores the spartition name order.
        self.table.setCornerButtonEnabled(True)
        corner = self.table.findChild(QtWidgets.QAbstractButton)
        if corner is not None:
            corner.setToolTip("Sort spartitions by name")
            corner.clicked.connect(self.sort_by_name)

    def sort_by_score(self, section: int):
        if not self.source_model:
            return
        self.source_model.sort_by_score(section)
        self.table.resizeColumnsToContents()

    def sort_by_name(self):
        if not self.source_model:
            return
        self.source_model.sort_by_spartition_name()
        self.table.resizeColumnsToContents()

    def report_results(self, task_name: str, results: Results):
        self.results = results
        self.table.resizeColumnsToContents()

    def report_saved(self, results: ExportResults):
        msgBox = QtWidgets.QMessageBox(self.window())
        msgBox.setWindowModality(QtCore.Qt.WindowModal)
        msgBox.setWindowFlag(QtCore.Qt.WindowStaysOnTopHint)
        msgBox.setWindowTitle(app.config.title)
        msgBox.setIcon(QtWidgets.QMessageBox.Information)
        msgBox.setText(f"Saved {results.spartition_count} spartitions successfully!")
        msgBox.setInformativeText(
            f"Time taken: {human_readable_seconds(results.seconds_taken)}."
        )

        msgBox.addButton("Ok", QtWidgets.QMessageBox.RejectRole)
        msgBox.addButton("Visualize", QtWidgets.QMessageBox.AcceptRole)

        self.window().msgShow(msgBox)

        role = msgBox.buttonRole(msgBox.clickedButton())

        match role:
            case QtWidgets.QMessageBox.AcceptRole:
                self.propagate_results_to_model(VisualizeModel, results.output_path)
            case QtWidgets.QMessageBox.RejectRole:
                pass

    def propagate_results_to_model(self, klass, path: Path):
        model_index = app.model.items.find_task(klass)
        if model_index is None:
            model_index = app.model.items.add_task(klass())
        item = app.model.items.data(model_index, role=app.model.items.ItemRole)
        item.object.open(path)
        app.model.items.focus(model_index)

    def show_preview(self, spartition: str):
        if self.results is None:
            return
        if not self.results.individual_list:
            return

        subset = self.results.subset_table.get(spartition, None)
        if subset is None:
            return

        dialog = PreviewDialog(
            spartition,
            self.results.individual_list,
            subset,
            self.results.score_table.get(spartition, {}),
            self.window(),
        )
        dialog.destroyed.connect(lambda: self.previews.remove(dialog))
        self.previews.append(dialog)
        dialog.show()

    def open(self):
        filename, _ = QtWidgets.QFileDialog.getOpenFileName(
            parent=self.window(),
            caption=f"{app.config.title} - Open file",
        )
        if not filename:
            return
        self.object.open(Path(filename))

    def remove_selection(self):
        if not self.source_model:
            return

        # A whole row means that score, since any cell already means its
        # column, and a full row spans every column.
        rows = self.table.get_selected_rows()
        if rows:
            self.source_model.remove_rows(rows)
        else:
            columns = self.table.get_selected_columns()
            if not columns:
                return
            self.source_model.remove_columns(columns)

        self.table.clearSelection()

    def clear(self):
        self.object.clear()

    def save(self, key=None):
        if not self.source_model or not self.source_model.order:
            return

        filename, _ = QtWidgets.QFileDialog.getSaveFileName(
            parent=self.window(),
            caption=f"{app.config.title} - Save file",
            filter="SPART XML (*.xml)",
        )
        if not filename:
            return

        self.object.save_selection(
            Path(filename),
            self.source_model.get_spartitions(),
            self.source_model.get_keys(),
        )
