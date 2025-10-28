from PySide6 import QtWidgets, QtCore

from pathlib import Path

from itaxotools.common.utility import AttrDict
from itaxotools.taxi_gui import app
from itaxotools.taxi_gui.tasks.common.view import ProgressCard
from itaxotools.taxi_gui.view.cards import Card

from ..common.view import (
    BlastTaskView,
    GraphicTitleCard,
    PathSelector,
)
from . import long_description, pixmap_medium, title
from .model import BooleanFilterProxyModel


class PathFileSelector(PathSelector):
    def _handle_browse(self, *args):
        filename, _ = QtWidgets.QFileDialog.getOpenFileName(
            parent=self.window(),
            caption=f"{app.config.title} - Browse file",
        )
        if not filename:
            return
        self.selectedPath.emit(Path(filename))


class PathFileOutSelector(PathSelector):
    def _handle_browse(self, *args, **kwargs):
        filename, _ = QtWidgets.QFileDialog.getSaveFileName(
            parent=self.window(),
            caption=f"{app.config.title} - Save file",
            filter="SPART XML (*.xml)",
        )
        if not filename:
            return
        self.selectedPath.emit(Path(filename))


class WeightDelegate(QtWidgets.QStyledItemDelegate):
    def createEditor(self, parent, option, index):
        editor = QtWidgets.QDoubleSpinBox(parent)
        editor.setDecimals(2)
        editor.setSingleStep(0.1)
        return editor


class CheckableTableView(QtWidgets.QTableView):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._max_rows = 18
        self._min_height = 120
        self._weight_delegate = WeightDelegate()
        self.setItemDelegateForColumn(5, self._weight_delegate)
        self.resize_height_to_contents()

    def mouseDoubleClickEvent(self, event):
        index = self.indexAt(event.position().toPoint())
        if not index.isValid():
            return super().mouseDoubleClickEvent(event)

        if not index.flags() & QtCore.Qt.ItemIsEnabled:
            return super().mouseDoubleClickEvent(event)

        model = index.model()
        row = index.row()
        col = index.column()

        checkbox_index = model.index(row, 0)

        if col < 5:
            current = model.data(checkbox_index, QtCore.Qt.CheckStateRole)
            new_state = (
                QtCore.Qt.CheckState.Unchecked
                if current == QtCore.Qt.CheckState.Checked
                else QtCore.Qt.CheckState.Checked
            )
            model.setData(checkbox_index, new_state, QtCore.Qt.CheckStateRole)
        else:
            return super().mouseDoubleClickEvent(event)

    def resize_height_to_contents(self):
        if not self.model():
            return self._resize_height_to_minimum()

        row_count = min(self.model().rowCount(), self._max_rows)
        if row_count == 0:
            return self._resize_height_to_minimum()

        height = self.horizontalHeader().height()
        for row in range(row_count):
            height += self.rowHeight(row)
        height += 2 * self.frameWidth()

        self.setFixedHeight(height)
        self.resize(self.width(), height)

    def _resize_height_to_minimum(self):
        self.setFixedHeight(self._min_height)
        self.resize(self.width(), self._min_height)


class ConcordanceTableCard(Card):
    toggled_bool_only = QtCore.Signal(bool)

    def __init__(self, text, parent=None):
        super().__init__(parent)
        self.draw_main(text)

    def draw_main(self, text):
        label = QtWidgets.QLabel(text + ":")
        label.setStyleSheet("""font-size: 16px;""")
        label.setMinimumWidth(150)

        view = CheckableTableView()
        view.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        view.setSortingEnabled(True)
        header = view.horizontalHeader()
        header.setStretchLastSection(True)

        checkbox = QtWidgets.QCheckBox(
            "Show boolean discrimination data types only (the rest are ignored anyway)"
        )
        checkbox.toggled.connect(self.toggled_bool_only)

        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(label)
        layout.addSpacing(8)
        layout.addWidget(view, 1)
        layout.addWidget(checkbox)
        layout.setSpacing(8)
        self.addLayout(layout)

        self.controls.view = view
        self.controls.bool_only = checkbox

    def set_model(self, model: QtCore.QAbstractTableModel):
        bool_proxy = BooleanFilterProxyModel()
        bool_proxy.setSourceModel(model)
        bool_proxy.show_boolean_only(True)

        sort_proxy = QtCore.QSortFilterProxyModel()
        sort_proxy.setSourceModel(bool_proxy)
        sort_proxy.setSortCaseSensitivity(QtCore.Qt.CaseInsensitive)
        sort_proxy.setDynamicSortFilter(True)

        self.controls.view.setModel(sort_proxy)
        self.controls.bool_proxy = bool_proxy

    def set_bool_only(self, value: bool):
        self.controls.bool_only.setChecked(value)
        self.controls.bool_proxy.show_boolean_only(value)
        self.resize_view()

    def resize_view(self):
        self.controls.view.resizeColumnsToContents()
        self.controls.view.resize_height_to_contents()


class View(BlastTaskView):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.draw_cards()

    def draw_cards(self):
        self.cards = AttrDict()
        self.cards.title = GraphicTitleCard(
            title, long_description, pixmap_medium.resource, self
        )
        self.cards.progress = ProgressCard(self)
        self.cards.concordances = PathFileSelector("\u25C0  Input", self)
        self.cards.output = PathFileOutSelector("\u25B6  Output", self)
        self.cards.table = ConcordanceTableCard("\u25E6  Concordance weights", self)

        self.cards.concordances.set_placeholder_text(
            "SPART XML file conbtaining concordances"
        )
        self.cards.output.set_placeholder_text(
            "Resulting SPART XML file with concordance scores"
        )

        layout = QtWidgets.QVBoxLayout()
        for card in self.cards:
            layout.addWidget(card)
        layout.addStretch(1)
        layout.setSpacing(6)
        layout.setContentsMargins(6, 6, 6, 6)

        self.setLayout(layout)

    def setObject(self, object):
        self.object = object
        self.binder.unbind_all()

        self.cards.table.set_model(self.object.concordances)
        self.binder.bind(object.concordances.rowsInserted, self.cards.table.resize_view)
        self.binder.bind(object.concordances.rowsRemoved, self.cards.table.resize_view)

        self.binder.bind(object.notification, self.showNotification)
        self.binder.bind(object.report_results, self.report_results)
        self.binder.bind(object.progression, self.cards.progress.showProgress)

        self.binder.bind(object.properties.name, self.cards.title.setTitle)
        self.binder.bind(object.properties.busy, self.cards.progress.setVisible)

        self.binder.bind(
            object.properties.concordance_path, self.cards.concordances.set_path
        )
        self.binder.bind(self.cards.concordances.selectedPath, object.open)

        self.binder.bind(object.properties.bool_only, self.cards.table.set_bool_only)
        self.binder.bind(
            self.cards.table.toggled_bool_only, object.properties.bool_only
        )

        self.binder.bind(object.properties.output_path, self.cards.output.set_path)
        self.binder.bind(self.cards.output.selectedPath, object.properties.output_path)

        self.binder.bind(object.properties.editable, self.setEditable)

    def setEditable(self, editable: bool):
        for card in self.cards:
            card.setEnabled(editable)
        self.cards.title.setEnabled(True)
        self.cards.progress.setEnabled(True)

    def open(self):
        filename, _ = QtWidgets.QFileDialog.getOpenFileName(
            parent=self.window(),
            caption=f"{app.config.title} - Open file",
        )
        if not filename:
            return
        self.object.open(Path(filename))
