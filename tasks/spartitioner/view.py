from PySide6 import QtCore, QtGui, QtWidgets

import json
from pathlib import Path

from itaxotools.taxi_gui import app
from itaxotools.taxi_gui.types import Notification
from itaxotools.taxi_gui.utility import human_readable_seconds
from itaxotools.taxi_gui.view.tasks import TaskView

from .model import Document
from .types import MIME_INDIVIDUALS, SaveResults


# Square tabs in the palette roles the rest of the interface is drawn with:
# the selected tab is one piece with its page, like a card on the dark view.
TAB_STYLE = """
    QTabWidget::pane {
        border: none;
        background: Palette(Midlight);
    }
    QTabBar {
        background: transparent;
        qproperty-drawBase: 0;
    }
    QTabBar::tab {
        background: Palette(Mid);
        color: Palette(Text);
        border: none;
        border-radius: 0px;
        min-width: 120px;
        padding: 8px 16px;
        margin-right: 4px;
        font-size: 14px;
    }
    QTabBar::tab:selected {
        background: Palette(Midlight);
    }
    QTabBar::tab:hover:!selected {
        background: Palette(Highlight);
        color: Palette(Light);
    }
"""


# Shared by the subset columns and the area that adds a new one.
SUBSET_WIDTH = 180

# Space to the sides of the text in a column header.
HEADER_PADDING = 2


class Separator(QtWidgets.QFrame):
    """A horizontal line between the controls of a page and its contents."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(1)
        self.setStyleSheet("background: Palette(Mid);")


class IndividualDragList(QtWidgets.QListWidget):
    """A list of individuals that can be dragged to and from other lists.

    Drops are only reported, never applied: the document decides what moves,
    and the lists are redrawn from it.
    """

    individualsDropped = QtCore.Signal(list)
    deleteRequested = QtCore.Signal(list)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setSelectionMode(QtWidgets.QAbstractItemView.ExtendedSelection)
        self.setDragDropMode(QtWidgets.QAbstractItemView.DragDrop)
        self.setDefaultDropAction(QtCore.Qt.MoveAction)
        self.setAlternatingRowColors(True)

    def get_selected_names(self) -> list[str]:
        return [item.text() for item in self.selectedItems()]

    def startDrag(self, supported_actions):
        names = self.get_selected_names()
        if not names:
            return
        mime = QtCore.QMimeData()
        mime.setData(MIME_INDIVIDUALS, json.dumps(names).encode())
        drag = QtGui.QDrag(self)
        drag.setMimeData(mime)
        drag.exec(QtCore.Qt.MoveAction)

    def _accepts(self, event) -> bool:
        if event.source() is self:
            return False
        return event.mimeData().hasFormat(MIME_INDIVIDUALS)

    def dragEnterEvent(self, event):
        if self._accepts(event):
            event.acceptProposedAction()
        else:
            event.ignore()

    def dragMoveEvent(self, event):
        if self._accepts(event):
            event.acceptProposedAction()
        else:
            event.ignore()

    def dropEvent(self, event):
        if not self._accepts(event):
            event.ignore()
            return
        data = bytes(event.mimeData().data(MIME_INDIVIDUALS))
        event.acceptProposedAction()
        self.individualsDropped.emit(json.loads(data.decode()))

    def keyPressEvent(self, event):
        if event.key() in (QtCore.Qt.Key_Delete, QtCore.Qt.Key_Backspace):
            names = self.get_selected_names()
            if names:
                self.deleteRequested.emit(names)
            return
        super().keyPressEvent(event)

    def set_names(self, names: list[str]):
        current = [self.item(row).text() for row in range(self.count())]
        if current == names:
            return
        self.clear()
        self.addItems(names)

    def select_names(self, names: list[str]):
        self.clearSelection()
        chosen = set(names)
        first = None
        for row in range(self.count()):
            item = self.item(row)
            if item.text() in chosen:
                item.setSelected(True)
                first = first or item
        if first is not None:
            self.scrollToItem(first)
            self.setCurrentItem(first, QtCore.QItemSelectionModel.NoUpdate)


class SubsetColumn(QtWidgets.QFrame):
    """One subset: an editable name on top of its individuals."""

    renameRequested = QtCore.Signal(str)
    deleteRequested = QtCore.Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFrameShape(QtWidgets.QFrame.StyledPanel)
        self.setFixedWidth(SUBSET_WIDTH)
        self.label = ""

        self.name = QtWidgets.QLineEdit()
        self.name.setPlaceholderText("Subset name")
        self.name.setTextMargins(HEADER_PADDING, 0, HEADER_PADDING, 0)
        self.name.setToolTip("Subset name, click to rename")
        self.name.editingFinished.connect(self._handle_editing_finished)

        self.remove = QtWidgets.QToolButton()
        self.remove.setText("✕")
        self.remove.setAutoRaise(True)
        self.remove.setToolTip("Delete this subset")
        self.remove.clicked.connect(self.deleteRequested)

        self.count = QtWidgets.QLabel()

        self.list = IndividualDragList()

        header = QtWidgets.QHBoxLayout()
        header.setSpacing(4)
        header.addWidget(self.name, 1)
        header.addWidget(self.remove)

        layout = QtWidgets.QVBoxLayout()
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(4)
        layout.addLayout(header)
        layout.addWidget(self.list, 1)
        layout.addWidget(self.count)
        self.setLayout(layout)

    def _handle_editing_finished(self):
        text = self.name.text().strip()
        if text != self.label:
            self.renameRequested.emit(text)

    def set_subset(self, label: str, names: list[str]):
        self.label = label
        if self.name.text() != label:
            self.name.setText(label)
        self.list.set_names(names)
        self.count.setText(f"{len(names)} individuals")


class NewSubsetTarget(QtWidgets.QPushButton):
    """Click for an empty subset, or drop individuals to start one with them."""

    individualsDropped = QtCore.Signal(list)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedWidth(SUBSET_WIDTH)
        self.setSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Expanding)
        # The labels are as faint as the outline, so the area reads as empty.
        self.setStyleSheet(
            """
            NewSubsetTarget {
                border: none;
                background: transparent;
            }
            NewSubsetTarget:hover {
                background: rgba(255, 255, 255, 90);
            }
            QLabel {
                color: rgba(0, 0, 0, 90);
            }
            """
        )

        # A button only has one text in one size, hence the labels on top.
        title = QtWidgets.QLabel("New subset")
        title.setStyleSheet("font-size: 18px;")
        hint = QtWidgets.QLabel("Click or\ndrag individuals here")
        for label in [title, hint]:
            label.setAlignment(QtCore.Qt.AlignCenter)
            label.setWordWrap(True)
            label.setAttribute(QtCore.Qt.WA_TransparentForMouseEvents)

        layout = QtWidgets.QVBoxLayout()
        layout.setContentsMargins(4, 12, 4, 12)
        layout.setSpacing(6)
        layout.addStretch(1)
        layout.addWidget(title)
        layout.addWidget(hint)
        layout.addStretch(1)
        self.setLayout(layout)
        self.setToolTip("Click to add a subset, or drop individuals here")
        self.setAcceptDrops(True)

    def paintEvent(self, event):
        super().paintEvent(event)
        # A stylesheet border ties the dash length to the line width, which
        # at one pixel gives dots. Drawing it here keeps the dashes long.
        pen = QtGui.QPen(QtGui.QColor(0, 0, 0, 50), 1)
        pen.setDashPattern([6, 4])
        pen.setCapStyle(QtCore.Qt.FlatCap)
        painter = QtGui.QPainter(self)
        painter.setPen(pen)
        painter.drawRect(self.rect().adjusted(0, 0, -1, -1))
        painter.end()

    def dragEnterEvent(self, event):
        if event.mimeData().hasFormat(MIME_INDIVIDUALS):
            event.acceptProposedAction()

    def dragMoveEvent(self, event):
        if event.mimeData().hasFormat(MIME_INDIVIDUALS):
            event.acceptProposedAction()

    def dropEvent(self, event):
        data = bytes(event.mimeData().data(MIME_INDIVIDUALS))
        event.acceptProposedAction()
        self.individualsDropped.emit(json.loads(data.decode()))


class IndividualsPage(QtWidgets.QWidget):
    """Individuals are typed in as plain text, one per line."""

    importRequested = QtCore.Signal()
    textEdited = QtCore.Signal()

    def __init__(self, parent=None):
        super().__init__(parent)

        self.import_button = QtWidgets.QPushButton("Import")
        self.import_button.setToolTip(
            "Add the individuals of a FASTA or SPART XML file"
        )
        self.import_button.clicked.connect(self.importRequested)

        self.clear_button = QtWidgets.QPushButton("Clear")
        self.clear_button.setToolTip("Remove all individuals from the list")
        self.clear_button.clicked.connect(self._handle_clear)

        self.editor = QtWidgets.QPlainTextEdit()
        self.editor.setPlaceholderText(
            "Type or paste the individuals here, one per line"
        )
        self.editor.setLineWrapMode(QtWidgets.QPlainTextEdit.NoWrap)
        self.editor.textChanged.connect(self._handle_text_changed)

        self.count = QtWidgets.QLabel()

        # As wide as the buttons of the other tasks.
        for button in [self.import_button, self.clear_button]:
            button.setFixedWidth(120)

        buttons = QtWidgets.QHBoxLayout()
        buttons.setSpacing(6)
        buttons.addWidget(self.import_button)
        buttons.addWidget(self.clear_button)
        buttons.addStretch(1)

        layout = QtWidgets.QVBoxLayout()
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)
        layout.addLayout(buttons)
        layout.addWidget(Separator())
        layout.addWidget(self.editor, 1)
        layout.addWidget(self.count)
        self.setLayout(layout)

        self._loading = False
        self._update_count()

    def _handle_clear(self):
        self.editor.clear()

    def _handle_text_changed(self):
        self._update_count()
        if not self._loading:
            self.textEdited.emit()

    def _update_count(self):
        self.count.setText(f"{len(self.get_names())} individuals")

    def get_lines(self) -> list[str]:
        lines = self.editor.toPlainText().splitlines()
        return [line.strip() for line in lines if line.strip()]

    def get_names(self) -> list[str]:
        """Every individual once, in the order first typed."""
        return list(dict.fromkeys(self.get_lines()))

    def set_names(self, names: list[str]):
        """Show the given individuals without reporting it as an edit."""
        self._loading = True
        self.editor.setPlainText("\n".join(names))
        self._loading = False

    def add_names(self, names: list[str]) -> int:
        present = set(self.get_names())
        added = [name for name in dict.fromkeys(names) if name not in present]
        if added:
            self.editor.setPlainText("\n".join(self.get_names() + added))
        return len(added)


class SpartitionPage(QtWidgets.QWidget):
    """All individuals on the left, one column per subset on the right."""

    failed = QtCore.Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.document: Document | None = None
        self.columns: list[SubsetColumn] = []

        self.combo = QtWidgets.QComboBox()
        self.combo.setMinimumWidth(200)
        self.combo.setToolTip("The spartition being edited")

        self.new_button = QtWidgets.QPushButton("New")
        self.new_button.setToolTip("Add a spartition")

        self.rename_button = QtWidgets.QPushButton("Rename")
        self.rename_button.setToolTip("Rename this spartition")

        self.delete_button = QtWidgets.QPushButton("Delete")
        self.delete_button.setToolTip("Delete this spartition")

        # As wide as the buttons of the other tasks.
        for button in [self.new_button, self.rename_button, self.delete_button]:
            button.setFixedWidth(120)

        controls = QtWidgets.QHBoxLayout()
        controls.setSpacing(6)
        controls.addWidget(self.combo)
        controls.addWidget(self.new_button)
        controls.addWidget(self.rename_button)
        controls.addWidget(self.delete_button)
        controls.addStretch(1)

        self.individuals = IndividualDragList()
        self.individuals.setToolTip(
            "Drag individuals into a subset. "
            "Grey ones are already assigned: double-click to find them."
        )
        self.individuals.itemDoubleClicked.connect(self._handle_double_click)
        self.individuals.individualsDropped.connect(self._handle_unassign)

        # Laid out like a subset column, so that the two line up: the same
        # frame and margins, and a title as tall as the name of a subset.
        title = QtWidgets.QLabel("Individuals")
        title.setFixedHeight(QtWidgets.QLineEdit().sizeHint().height())
        title.setContentsMargins(HEADER_PADDING, 0, HEADER_PADDING, 0)
        self.summary = QtWidgets.QLabel()

        panel_layout = QtWidgets.QVBoxLayout()
        panel_layout.setContentsMargins(6, 6, 6, 6)
        panel_layout.setSpacing(4)
        panel_layout.addWidget(title)
        panel_layout.addWidget(self.individuals, 1)
        panel_layout.addWidget(self.summary)
        panel = QtWidgets.QFrame()
        panel.setFrameShape(QtWidgets.QFrame.StyledPanel)
        panel.setLayout(panel_layout)

        self.scroll = QtWidgets.QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QtWidgets.QFrame.NoFrame)
        # Always shown, so that the columns keep the same height, and the
        # individuals can be kept clear of it to end where the columns end.
        self.scroll.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOn)
        scroll_bar_height = self.scroll.horizontalScrollBar().sizeHint().height()

        left_layout = QtWidgets.QVBoxLayout()
        left_layout.setContentsMargins(0, 0, 0, scroll_bar_height)
        left_layout.addWidget(panel)
        left = QtWidgets.QWidget()
        left.setMinimumWidth(SUBSET_WIDTH)
        left.setLayout(left_layout)

        self.target = NewSubsetTarget()
        self.target.clicked.connect(self._handle_new_subset)
        self.target.individualsDropped.connect(self._handle_new_subset_dropped)

        self.column_layout = QtWidgets.QHBoxLayout()
        self.column_layout.setContentsMargins(0, 0, 0, 0)
        self.column_layout.setSpacing(6)
        self.column_layout.addWidget(self.target)
        self.column_layout.addStretch(1)

        container = QtWidgets.QWidget()
        container.setLayout(self.column_layout)

        self.scroll.setWidget(container)

        self.placeholder = QtWidgets.QLabel(
            "There are no spartitions yet. Use “New” to create one."
        )
        self.placeholder.setAlignment(QtCore.Qt.AlignCenter)

        self.stack = QtWidgets.QStackedWidget()
        self.stack.addWidget(self.placeholder)
        self.stack.addWidget(self.scroll)

        splitter = QtWidgets.QSplitter(QtCore.Qt.Horizontal)
        splitter.addWidget(left)
        splitter.addWidget(self.stack)
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        splitter.setSizes([SUBSET_WIDTH, 600])
        splitter.setChildrenCollapsible(False)
        # The same gap as between the subset columns.
        splitter.setHandleWidth(6)

        layout = QtWidgets.QVBoxLayout()
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)
        layout.addLayout(controls)
        layout.addWidget(Separator())
        layout.addWidget(splitter, 1)
        self.setLayout(layout)

    def set_document(self, document: Document):
        self.document = document
        self.refresh()

    def _attempt(self, action, *args):
        """Report invalid names instead of raising."""
        try:
            return action(*args)
        except ValueError as error:
            self.failed.emit(str(error))
            self.refresh()
            return None

    def _column_index(self, column: SubsetColumn) -> int:
        return self.columns.index(column)

    def _add_column(self):
        column = SubsetColumn()
        column.renameRequested.connect(
            lambda label, c=column: self._attempt(
                self.document.rename_subset, self._column_index(c), label
            )
        )
        column.deleteRequested.connect(
            lambda c=column: self.document.delete_subset(self._column_index(c))
        )
        column.list.individualsDropped.connect(
            lambda names, c=column: self.document.assign(names, self._column_index(c))
        )
        column.list.deleteRequested.connect(self._handle_unassign)
        self.column_layout.insertWidget(len(self.columns), column)
        self.columns.append(column)

    def _remove_column(self):
        column = self.columns.pop()
        self.column_layout.removeWidget(column)
        column.hide()
        column.deleteLater()

    def refresh(self):
        """Redraw everything from the document.

        Columns are reused by position rather than rebuilt, so that a widget
        is never destroyed while it is handling a drop or an edit.
        """
        if self.document is None:
            return

        spartition = self.document.get_current()
        self.stack.setCurrentWidget(
            self.placeholder if spartition is None else self.scroll
        )

        subsets = spartition.subsets if spartition is not None else []

        while len(self.columns) < len(subsets):
            self._add_column()
        while len(self.columns) > len(subsets):
            self._remove_column()
        for column, subset in zip(self.columns, subsets):
            column.set_subset(subset.label, subset.individuals)

        self.individuals.set_names(self.document.individuals)
        assigned = spartition.assigned() if spartition is not None else set()
        palette = self.individuals.palette()
        normal = palette.brush(QtGui.QPalette.Active, QtGui.QPalette.Text)
        grey = palette.brush(QtGui.QPalette.Disabled, QtGui.QPalette.Text)
        for row in range(self.individuals.count()):
            item = self.individuals.item(row)
            item.setForeground(grey if item.text() in assigned else normal)

        total = len(self.document.individuals)
        if spartition is None:
            self.summary.setText(f"{total} individuals")
        else:
            self.summary.setText(f"{len(assigned)} of {total} assigned")

    def _handle_unassign(self, names: list[str]):
        self.document.unassign(names)

    def _handle_new_subset(self):
        index = self.document.add_subset()
        if index is not None:
            self.show_column(index)

    def _handle_new_subset_dropped(self, names: list[str]):
        index = self.document.add_subset()
        if index is not None:
            self.document.assign(names, index)
            self.show_column(index)

    def _handle_double_click(self, item):
        """Find where an assigned individual went."""
        spartition = self.document.get_current()
        if spartition is None:
            return
        index = spartition.subset_of(item.text())
        if index is None:
            return
        for column in self.columns:
            column.list.clearSelection()
        self.show_column(index)
        column = self.columns[index]
        column.list.select_names([item.text()])
        column.list.setFocus()

    def show_column(self, index: int):
        column = self.columns[index]
        # The column only gets its place once the layout has run.
        QtCore.QTimer.singleShot(0, lambda: self.scroll.ensureWidgetVisible(column))


class View(TaskView):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.draw()

    def draw(self):
        self.individuals_page = IndividualsPage()
        self.individuals_page.importRequested.connect(self.import_individuals)
        self.individuals_page.textEdited.connect(self._handle_text_edited)

        self.spartition_page = SpartitionPage()
        self.spartition_page.failed.connect(self.show_warning)
        self.spartition_page.combo.activated.connect(self._handle_combo_activated)
        self.spartition_page.new_button.clicked.connect(self.new_spartition)
        self.spartition_page.rename_button.clicked.connect(self.rename_spartition)
        self.spartition_page.delete_button.clicked.connect(self.delete_spartition)
        self.combo = self.spartition_page.combo

        self.pages = QtWidgets.QTabWidget()
        self.pages.setStyleSheet(TAB_STYLE)
        for page in [self.individuals_page, self.spartition_page]:
            page.setAutoFillBackground(True)
            page.setBackgroundRole(QtGui.QPalette.Midlight)
        self.pages.addTab(self.individuals_page, "Individuals")
        self.pages.addTab(self.spartition_page, "Spartitions")
        self.pages.setTabToolTip(0, "Define the individuals")
        self.pages.setTabToolTip(1, "Assign the individuals to subsets")
        self.pages.currentChanged.connect(self._handle_tab_changed)
        self._switching = False

        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(self.pages, 1)
        layout.setContentsMargins(6, 6, 6, 6)
        self.setLayout(layout)

        self.update_actions()

    def setObject(self, object):
        self.object = object
        self.binder.unbind_all()

        self.binder.bind(object.notification, self.showNotification)
        self.binder.bind(object.report_saved, self.report_saved)
        self.binder.bind(object.report_imported, self.report_imported)

        document = object.document
        self.binder.bind(document.individualsChanged, self._handle_individuals_changed)
        self.binder.bind(document.spartitionsChanged, self._handle_spartitions_changed)
        self.binder.bind(document.currentChanged, self._handle_current_changed)
        self.binder.bind(document.subsetsChanged, self.spartition_page.refresh)

        self.spartition_page.set_document(document)
        self._handle_individuals_changed()
        self._handle_spartitions_changed()

    @property
    def document(self) -> Document:
        return self.object.document

    def show_warning(self, text: str):
        self.showNotification(Notification.Warn(text))

    def is_editing_individuals(self) -> bool:
        return self.pages.currentWidget() is self.individuals_page

    def update_actions(self):
        has_current = bool(self.object and self.document.get_current())
        self.combo.setEnabled(has_current)
        self.spartition_page.rename_button.setEnabled(has_current)
        self.spartition_page.delete_button.setEnabled(has_current)

    # Document changes

    def _handle_individuals_changed(self):
        if self.individuals_page.get_names() != self.document.individuals:
            self.individuals_page.set_names(self.document.individuals)
        self.spartition_page.refresh()

    def _handle_spartitions_changed(self):
        self.combo.blockSignals(True)
        self.combo.clear()
        self.combo.addItems(self.document.get_spartition_labels())
        self.combo.setCurrentIndex(self.document.current)
        self.combo.blockSignals(False)
        self.update_actions()

    def _handle_current_changed(self):
        self.combo.blockSignals(True)
        self.combo.setCurrentIndex(self.document.current)
        self.combo.blockSignals(False)
        self.spartition_page.refresh()
        self.update_actions()

    # Individuals

    def _handle_text_edited(self):
        self.object.set_draft(bool(self.individuals_page.get_names()))

    def commit_individuals(self) -> bool:
        """Hand the typed individuals over to the document.

        Returns False if the user backed out of removing assigned individuals.
        """
        lines = self.individuals_page.get_lines()
        names = self.individuals_page.get_names()

        kept = set(names)
        removed = [name for name in self.document.individuals if name not in kept]
        lost = self.document.get_assigned_anywhere(removed)
        if lost:
            listed = ", ".join(lost[:5])
            if len(lost) > 5:
                listed += f" and {len(lost) - 5} more"
            if not self.getConfirmation(
                "Remove individuals",
                f"{len(lost)} individuals that were assigned to subsets are no "
                f"longer listed, and will be removed from them: {listed}.\n\n"
                "Continue?",
            ):
                return False

        if len(names) != len(lines):
            self.individuals_page.set_names(names)
            self.show_warning(
                f"{len(lines) - len(names)} duplicate individuals were removed."
            )

        self.document.set_individuals(names)
        self.object.set_draft(False)
        return True

    def import_individuals(self):
        filename, _ = QtWidgets.QFileDialog.getOpenFileName(
            parent=self.window(),
            caption=f"{app.config.title} - Import individuals",
            filter="FASTA or SPART XML (*.fas *.fa *.fasta *.xml);;All files (*)",
        )
        if not filename:
            return
        self.object.import_individuals(Path(filename))

    def report_imported(self, names: list[str]):
        added = self.individuals_page.add_names(names)
        self._handle_text_edited()
        skipped = len(set(names)) - added
        text = f"Imported {added} individuals."
        if skipped:
            text += f"\n{skipped} were already listed."
        self.showNotification(Notification.Info(text))

    # Tabs

    def show_page(self, page: QtWidgets.QWidget):
        """Switch tabs without the checks of a switch made by the user."""
        self._switching = True
        self.pages.setCurrentWidget(page)
        self._switching = False
        self.update_actions()

    def _handle_tab_changed(self, index: int):
        if self._switching:
            return
        if self.pages.widget(index) is self.spartition_page:
            if not self.commit_individuals():
                self.show_page(self.individuals_page)
                return
            self.spartition_page.refresh()
        self.update_actions()

    def show_spartitions(self):
        self.show_page(self.spartition_page)

    # Spartitions

    def _handle_combo_activated(self, index: int):
        self.document.set_current(index)

    def _ask_label(self, caption: str, text: str) -> str | None:
        label, ok = QtWidgets.QInputDialog.getText(
            self.window(),
            f"{app.config.title} - {caption}",
            "Spartition name:",
            text=text,
        )
        if not ok:
            return None
        return label.strip()

    def new_spartition(self):
        label = self._ask_label(
            "New spartition", self.document.suggest_spartition_label()
        )
        if label is None:
            return
        try:
            self.document.add_spartition(label)
        except ValueError as error:
            self.show_warning(str(error))

    def rename_spartition(self):
        spartition = self.document.get_current()
        if spartition is None:
            return
        label = self._ask_label("Rename spartition", spartition.label)
        if label is None:
            return
        try:
            self.document.rename_spartition(label)
        except ValueError as error:
            self.show_warning(str(error))

    def delete_spartition(self):
        spartition = self.document.get_current()
        if spartition is None:
            return
        if not self.getConfirmation(
            "Delete spartition",
            f"Delete spartition {repr(spartition.label)} and all its subsets?",
        ):
            return
        self.document.delete_spartition()

    # Toolbar

    def has_unsaved_changes(self) -> bool:
        return self.document.modified or self.object.has_draft

    def open(self):
        if self.has_unsaved_changes() and not self.getConfirmation(
            "Open file", "Discard all unsaved changes and open another file?"
        ):
            return
        filename, _ = QtWidgets.QFileDialog.getOpenFileName(
            parent=self.window(),
            caption=f"{app.config.title} - Open file",
            filter="SPART XML (*.xml);;All files (*)",
        )
        if not filename:
            return
        self.object.set_draft(False)
        self.object.open(Path(filename))
        self.show_spartitions()

    def save(self, key=None):
        if not self.commit_individuals():
            return

        if not self.document.individuals:
            self.show_warning("There are no individuals to save.")
            return

        if not self.confirm_unassigned():
            return

        # The dialog itself asks before overwriting an existing file.
        filename, _ = QtWidgets.QFileDialog.getSaveFileName(
            parent=self.window(),
            caption=f"{app.config.title} - Save file",
            filter="SPART XML (*.xml)",
        )
        if not filename:
            return
        self.object.save(Path(filename))

    def confirm_unassigned(self) -> bool:
        counts = self.document.get_unassigned_counts()
        if not counts:
            return True

        msgBox = QtWidgets.QMessageBox(self.window())
        msgBox.setWindowTitle(f"{app.config.title} - Unassigned individuals")
        msgBox.setIcon(QtWidgets.QMessageBox.Warning)
        msgBox.setText("Some individuals are not assigned to any subset.")
        msgBox.setInformativeText(
            "They will be left out of these spartitions:\n\n"
            + "\n".join(
                f"{label}: {count} unassigned" for label, count in counts.items()
            )
        )
        save = msgBox.addButton("Save anyway", QtWidgets.QMessageBox.AcceptRole)
        msgBox.addButton(QtWidgets.QMessageBox.Cancel)
        msgBox.setDefaultButton(QtWidgets.QMessageBox.Cancel)
        self.window().msgShow(msgBox)
        return msgBox.clickedButton() is save

    def report_saved(self, results: SaveResults):
        msgBox = QtWidgets.QMessageBox(self.window())
        msgBox.setWindowTitle(app.config.title)
        msgBox.setIcon(QtWidgets.QMessageBox.Information)
        msgBox.setText(f"Saved {results.spartition_count} spartitions successfully!")
        msgBox.setInformativeText(
            f"Time taken: {human_readable_seconds(results.seconds_taken)}."
        )
        msgBox.setStandardButtons(QtWidgets.QMessageBox.Ok)
        self.window().msgShow(msgBox)

    def clear(self):
        if not self.getConfirmation(
            "Clear", "Discard all individuals and spartitions?"
        ):
            return
        self.object.clear()
        self.show_page(self.individuals_page)
