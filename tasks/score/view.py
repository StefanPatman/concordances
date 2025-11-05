from PySide6 import QtWidgets, QtCore, QtGui

from pathlib import Path

from itaxotools.common.utility import AttrDict
from itaxotools.taxi_gui import app
from itaxotools.taxi_gui.tasks.common.view import ProgressCard
from itaxotools.taxi_gui.view.cards import Card
from itaxotools.taxi_gui.view.animations import VerticalRollAnimation
from itaxotools.taxi_gui.utility import human_readable_seconds

from ..common.widgets import GrowingTextEdit
from ..common.view import (
    BlastTaskView,
    GraphicTitleCard,
    PathSelector,
    OptionCard,
)
from ..common.types import Results
from ..visualize.model import Model as VisualizeModel

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


class ConcordanceTableView(QtWidgets.QTableView):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._max_rows = 18
        self._min_height = 120
        self._weight_delegate = WeightDelegate()
        self.setItemDelegateForColumn(5, self._weight_delegate)

        self.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.setSortingEnabled(True)
        header = self.horizontalHeader()
        header.setStretchLastSection(True)

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

        view = ConcordanceTableView()

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


class EvidenceTypeTableView(QtWidgets.QTableView):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._max_rows = 6
        self._min_height = 80
        self._weight_delegate = WeightDelegate()
        self.setItemDelegateForColumn(1, self._weight_delegate)

        self.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.setSortingEnabled(True)
        header = self.horizontalHeader()
        header.setStretchLastSection(True)

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

        checkbox_index = model.index(row, 2)

        if col != 1:
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


class EvidenceTypeTableCard(Card):
    toggled_bool_only = QtCore.Signal(bool)

    def __init__(self, text, parent=None):
        super().__init__(parent)
        self.draw_main(text)

    def draw_main(self, text):
        label = QtWidgets.QLabel(text + ":")
        label.setStyleSheet("""font-size: 16px;""")
        label.setMinimumWidth(150)

        view = EvidenceTypeTableView()

        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(label)
        layout.addSpacing(8)
        layout.addWidget(view, 1)
        layout.setSpacing(8)
        self.addLayout(layout)

        self.controls.view = view

    def set_model(self, model: QtCore.QAbstractTableModel):
        sort_proxy = QtCore.QSortFilterProxyModel()
        sort_proxy.setSourceModel(model)
        sort_proxy.setSortCaseSensitivity(QtCore.Qt.CaseInsensitive)
        sort_proxy.setDynamicSortFilter(True)

        self.controls.view.setModel(sort_proxy)

    def resize_view(self):
        self.controls.view.resizeColumnsToContents()
        self.controls.view.resize_height_to_contents()


class IndividualRestrainsView(OptionCard):
    individualActivated = QtCore.Signal(str)
    list_placeholder = (
        "List of individuals, one per line."
        "\n"
        "Groups are separated by one or more empty lines."
        "\n"
        "Double-click an item on the right to add it."
        "\n"
        "\n"
        "Example:"
        "\n"
        "\n"
        "group_A_individual_1"
        "\n"
        "group_A_individual_2"
        "\n"
        "group_A_individual_3"
        "\n"
        "\n"
        "group_B_individual_4"
        "\n"
        "group_B_individual_5"
        "\n"
    )

    def __init__(self, text, parent=None):
        super().__init__(text, "", parent)
        self.draw_main(text)
        self.individualActivated.connect(self._insert_individual)

    def draw_main(self, text):
        list = GrowingTextEdit()
        list.document().setDocumentMargin(8)
        list.setPlaceholderText(self.list_placeholder)

        view = QtWidgets.QListView()
        search = QtWidgets.QLineEdit()

        fixed_font = QtGui.QFontDatabase.systemFont(QtGui.QFontDatabase.FixedFont)
        list.setFont(fixed_font)
        view.setFont(fixed_font)

        view.doubleClicked.connect(self._handle_double_clicked)
        search.textChanged.connect(self._handle_search_text)

        layout = QtWidgets.QGridLayout()
        layout.setColumnStretch(0, 1)
        layout.addWidget(list, 0, 0, 2, 1)
        layout.addWidget(search, 0, 1, 1, 1)
        layout.addWidget(view, 1, 1, 1, 1)
        layout.setSpacing(8)

        widget = QtWidgets.QWidget()
        widget.setLayout(layout)
        widget.roll = VerticalRollAnimation(widget)
        self.addWidget(widget)

        self.controls.options_widget = widget
        self.controls.list = list
        self.controls.view = view
        self.controls.search = search

        self.toggled.connect(self.set_options_visible)

    def set_options_visible(self, value: bool):
        self.controls.options_widget.roll.setAnimatedVisible(value)

    def set_individuals_model(self, model: QtCore.QAbstractTableModel):
        proxy = QtCore.QSortFilterProxyModel()
        proxy.setSourceModel(model)
        proxy.setSortCaseSensitivity(QtCore.Qt.CaseInsensitive)
        proxy.setDynamicSortFilter(True)
        proxy.setFilterKeyColumn(0)

        self.controls.view.setModel(proxy)

    def _handle_search_text(self, text: str):
        proxy = self.controls.view.model()
        if not proxy:
            return

        proxy.setFilterFixedString(text)

    def _handle_double_clicked(self, index):
        proxy = self.controls.view.model()
        if not proxy:
            return

        source_model = proxy.sourceModel()
        source_index = proxy.mapToSource(index)
        name = source_model.data(source_index, QtCore.Qt.DisplayRole)
        if name:
            self.individualActivated.emit(name)

    def _insert_individual(self, name: str):
        text_edit = self.controls.list
        cursor = text_edit.textCursor()

        cursor.movePosition(QtGui.QTextCursor.EndOfBlock)

        block_text = cursor.block().text().strip()
        if block_text:
            cursor.insertText("\n")

        cursor.insertText(name)
        text_edit.setTextCursor(cursor)
        text_edit.ensureCursorVisible()


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
        self.cards.concordance_table = ConcordanceTableCard(
            "\u25E6  Concordance weights", self
        )
        self.cards.evidence_type_table = EvidenceTypeTableCard(
            "\u25E6  Evidence type weights", self
        )
        self.cards.conspecific_constraints = IndividualRestrainsView(
            "Conspecific constraints", self
        )
        self.cards.heterospecific_constraints = IndividualRestrainsView(
            "Heterospecific constraints", self
        )

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

        self.cards.concordance_table.set_model(self.object.concordances)
        self.binder.bind(
            object.concordances.rowsInserted, self.cards.concordance_table.resize_view
        )
        self.binder.bind(
            object.concordances.rowsRemoved, self.cards.concordance_table.resize_view
        )

        self.binder.bind(
            object.properties.bool_only, self.cards.concordance_table.set_bool_only
        )
        self.binder.bind(
            self.cards.concordance_table.toggled_bool_only, object.properties.bool_only
        )

        self.cards.evidence_type_table.set_model(self.object.evidence_types)
        self.binder.bind(
            object.evidence_types.rowsInserted,
            self.cards.evidence_type_table.resize_view,
        )
        self.binder.bind(
            object.evidence_types.rowsRemoved,
            self.cards.evidence_type_table.resize_view,
        )

        self.binder.bind(object.notification, self.showNotification)
        self.binder.bind(object.report_results, self.report_results)
        self.binder.bind(object.progression, self.cards.progress.showProgress)

        self.binder.bind(object.properties.name, self.cards.title.setTitle)
        self.binder.bind(object.properties.busy, self.cards.progress.setVisible)

        self.binder.bind(
            object.properties.concordance_path, self.cards.concordances.set_path
        )
        self.binder.bind(self.cards.concordances.selectedPath, object.open)

        self.binder.bind(object.properties.output_path, self.cards.output.set_path)
        self.binder.bind(self.cards.output.selectedPath, object.properties.output_path)

        self.cards.conspecific_constraints.set_individuals_model(
            self.object.individuals
        )
        self.cards.heterospecific_constraints.set_individuals_model(
            self.object.individuals
        )

        self.binder.bind(
            object.properties.conspecific_constraints_enabled,
            self.cards.conspecific_constraints.setChecked,
        )
        self.binder.bind(
            self.cards.conspecific_constraints.toggled,
            object.properties.conspecific_constraints_enabled,
        )
        self.binder.bind(
            object.properties.conspecific_constraints_text,
            self.cards.conspecific_constraints.controls.list.setText,
        )
        self.binder.bind(
            self.cards.conspecific_constraints.controls.list.textEditedSafe,
            object.properties.conspecific_constraints_text,
        )
        self.cards.conspecific_constraints.set_options_visible(
            object.conspecific_constraints_enabled
        )

        self.binder.bind(
            object.properties.heterospecific_constraints_enabled,
            self.cards.heterospecific_constraints.setChecked,
        )
        self.binder.bind(
            self.cards.heterospecific_constraints.toggled,
            object.properties.heterospecific_constraints_enabled,
        )
        self.binder.bind(
            object.properties.heterospecific_constraints_text,
            self.cards.heterospecific_constraints.controls.list.setText,
        )
        self.binder.bind(
            self.cards.heterospecific_constraints.controls.list.textEditedSafe,
            object.properties.heterospecific_constraints_text,
        )
        self.cards.heterospecific_constraints.set_options_visible(
            object.heterospecific_constraints_enabled
        )

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

    def report_results(self, task_name: str, results: Results):
        msgBox = QtWidgets.QMessageBox(self.window())
        msgBox.setWindowModality(QtCore.Qt.WindowModal)
        msgBox.setWindowFlag(QtCore.Qt.WindowStaysOnTopHint)
        msgBox.setWindowTitle(app.config.title)
        msgBox.setIcon(QtWidgets.QMessageBox.Information)
        msgBox.setText(f"{task_name} completed successfully!")
        msgBox.setInformativeText(
            f"Time taken: {human_readable_seconds(results.seconds_taken)}."
        )

        msgBox.addButton("Ok", QtWidgets.QMessageBox.RejectRole)
        msgBox.addButton("Visualize", QtWidgets.QMessageBox.AcceptRole)

        self.window().msgShow(msgBox)

        role = msgBox.buttonRole(msgBox.clickedButton())

        match role:
            case QtWidgets.QMessageBox.AcceptRole:
                self.propagate_reults_to_model(VisualizeModel, results)
            case QtWidgets.QMessageBox.RejectRole:
                pass

    def propagate_reults_to_model(self, klass, results: Results):
        model_index = app.model.items.find_task(klass)
        if model_index is None:
            model_index = app.model.items.add_task(klass())
        item = app.model.items.data(model_index, role=app.model.items.ItemRole)
        item.object.open(results.output_path)
        app.model.items.focus(model_index)
