from PySide6 import QtCore, QtWidgets

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
from ..common.widgets import GSpinBox, GDoubleSpinBox

from . import long_description, pixmap_medium, title


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


class PartitionTableView(QtWidgets.QTableView):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._max_rows = 10
        self._min_height = 80

        self.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAsNeeded)
        self.horizontalHeader().setStretchLastSection(True)
        self.verticalHeader().setVisible(False)

        self.resize_height_to_contents()

    def mouseDoubleClickEvent(self, event):
        index = self.indexAt(event.position().toPoint())
        if not index.isValid():
            return super().mouseDoubleClickEvent(event)
        if not index.flags() & QtCore.Qt.ItemIsEnabled:
            return super().mouseDoubleClickEvent(event)

        model = index.model()
        checkbox_index = model.index(index.row(), 0)
        current = model.data(checkbox_index, QtCore.Qt.CheckStateRole)
        new_state = (
            QtCore.Qt.CheckState.Unchecked
            if current == QtCore.Qt.CheckState.Checked
            else QtCore.Qt.CheckState.Checked
        )
        model.setData(checkbox_index, new_state, QtCore.Qt.CheckStateRole)

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


class PartitionTableCard(Card):
    requestSelectAll = QtCore.Signal()
    requestSelectNone = QtCore.Signal()

    def __init__(self, text, parent=None):
        super().__init__(parent)
        self.draw_main(text)

    def draw_main(self, text):
        label = QtWidgets.QLabel(text + ":")
        label.setStyleSheet("""font-size: 16px;""")
        label.setMinimumWidth(150)

        description = QtWidgets.QLabel(
            "Check the partitions to reshuffle. The options below are applied "
            "to each selected partition."
        )
        description.setWordWrap(True)

        view = PartitionTableView()

        select_all = QtWidgets.QPushButton("Select all")
        select_none = QtWidgets.QPushButton("Select none")
        select_all.clicked.connect(self.requestSelectAll)
        select_none.clicked.connect(self.requestSelectNone)

        buttons = QtWidgets.QHBoxLayout()
        buttons.setSpacing(8)
        buttons.addWidget(select_all)
        buttons.addWidget(select_none)
        buttons.addStretch(1)

        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(label)
        layout.addWidget(description)
        layout.addSpacing(4)
        layout.addWidget(view, 1)
        layout.addLayout(buttons)
        layout.setSpacing(8)
        self.addLayout(layout)

        self.controls.view = view

    def set_model(self, model: QtCore.QAbstractTableModel):
        view = self.controls.view
        view.setModel(model)
        header = view.horizontalHeader()
        header.setSectionResizeMode(0, QtWidgets.QHeaderView.Stretch)
        header.setSectionResizeMode(1, QtWidgets.QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QtWidgets.QHeaderView.ResizeToContents)
        self.resize_view()

    def resize_view(self):
        self.controls.view.resizeColumnsToContents()
        self.controls.view.resize_height_to_contents()


class ReshuffleOptionsCard(Card):
    rows = [
        (
            "add_partitions",
            "New partitions",
            "Append this many new partitions for each selected existing partition.",
        ),
        (
            "merge_count",
            "Total merges",
            "Randomly merge subsets of a partition into a single subset.",
        ),
        (
            "split_count",
            "Total splits",
            "Randomly split a subset of a partition into two subsets.",
        ),
        (
            "swap_count",
            "Total swaps",
            "Randomly swaps individuals between the subsets of a partition.",
        ),
    ]

    def __init__(self, parent=None):
        super().__init__(parent)
        self.draw_main()

    def draw_main(self):
        title = QtWidgets.QLabel("Reshuffling options:")
        title.setStyleSheet("""font-size: 16px;""")

        description = QtWidgets.QLabel(
            "These values are applied to each selected partition. "
            "Leave a value at zero to skip that operation."
        )
        description.setWordWrap(True)

        grid = QtWidgets.QGridLayout()
        grid.setContentsMargins(12, 0, 0, 0)
        grid.setHorizontalSpacing(16)
        grid.setVerticalSpacing(8)
        grid.setColumnStretch(2, 1)

        for row, (name, text, hint) in enumerate(self.rows):
            label = QtWidgets.QLabel(text + ":")
            label.setMinimumWidth(90)

            field = GSpinBox()
            field.setFixedWidth(120)
            field.setMinimum(0)
            field.setMaximum(2147483647)

            hint_label = QtWidgets.QLabel(hint)
            hint_label.setStyleSheet("""color: Palette(Shadow);""")

            grid.addWidget(label, row, 0)
            grid.addWidget(field, row, 1)
            grid.addWidget(hint_label, row, 2)

            self.controls[name] = field

        spread_row = len(self.rows)
        spread_label = QtWidgets.QLabel("Spread:")
        spread_label.setMinimumWidth(90)

        spread_field = GDoubleSpinBox()
        spread_field.setFixedWidth(120)
        spread_field.setMinimum(0.0)
        spread_field.setMaximum(5.0)
        spread_field.setSingleStep(0.05)
        spread_field.setDecimals(2)

        spread_hint = QtWidgets.QLabel(
            "Variation between new partitions: higher=uneven, lower=uniform."
        )
        spread_hint.setStyleSheet("""color: Palette(Shadow);""")

        grid.addWidget(spread_label, spread_row, 0)
        grid.addWidget(spread_field, spread_row, 1)
        grid.addWidget(spread_hint, spread_row, 2)

        self.controls["spread"] = spread_field

        layout = QtWidgets.QVBoxLayout()
        layout.setSpacing(12)
        layout.addWidget(title)
        layout.addWidget(description)
        layout.addLayout(grid)
        self.addLayout(layout)


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
        self.cards.input = PathFileSelector("◀  Input", self)
        self.cards.output = PathFileOutSelector("▶  Output", self)
        self.cards.partitions = PartitionTableCard("◦  Input partitions", self)
        self.cards.options = ReshuffleOptionsCard(self)

        self.cards.input.set_placeholder_text("SPART XML file to reshuffle")
        self.cards.output.set_placeholder_text(
            "Resulting SPART XML file with the reshuffled partitions"
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

        self.binder.bind(object.notification, self.showNotification)
        self.binder.bind(object.report_results, self.report_results)
        self.binder.bind(object.progression, self.cards.progress.showProgress)

        self.binder.bind(object.properties.name, self.cards.title.setTitle)
        self.binder.bind(object.properties.busy, self.cards.progress.setVisible)

        self.binder.bind(object.properties.input_path, self.cards.input.set_path)
        self.binder.bind(self.cards.input.selectedPath, object.open)

        self.binder.bind(object.properties.output_path, self.cards.output.set_path)
        self.binder.bind(self.cards.output.selectedPath, object.properties.output_path)

        self.cards.partitions.set_model(object.partitions)
        self.binder.bind(
            object.partitions.modelReset, self.cards.partitions.resize_view
        )
        self.binder.bind(
            self.cards.partitions.requestSelectAll,
            lambda: object.partitions.set_all_checked(True),
        )
        self.binder.bind(
            self.cards.partitions.requestSelectNone,
            lambda: object.partitions.set_all_checked(False),
        )

        for name, _, _ in ReshuffleOptionsCard.rows:
            field = self.cards.options.controls[name]
            property = getattr(object.properties, name)
            self.binder.bind(property, field.setValue)
            self.binder.bind(field.valueChangedSafe, property)

        spread_field = self.cards.options.controls["spread"]
        self.binder.bind(object.properties.spread, spread_field.setValue)
        self.binder.bind(spread_field.valueChangedSafe, object.properties.spread)

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
