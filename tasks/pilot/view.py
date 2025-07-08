from PySide6 import QtCore, QtWidgets, QtGui

from pathlib import Path

from itaxotools.common.utility import AttrDict
from itaxotools.taxi_gui import app
from itaxotools.taxi_gui.tasks.common.view import ProgressCard
from itaxotools.taxi_gui.view.animations import VerticalRollAnimation
from itaxotools.taxi_gui.view.cards import Card
from itaxotools.taxi_gui.view.widgets import NoWheelComboBox, RadioButtonGroup

from ..common.view import (
    BlastTaskView,
    GraphicTitleCard,
    PathSelector,
    BatchSequenceSelector,
)
from ..common.widgets import FloatPropertyLineEdit, IntPropertyLineEdit
from .types import SubstitutionModel
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


class OptionsSelector(Card):
    def __init__(self, parent=None):
        super().__init__(parent)
        label = QtWidgets.QLabel("\u2022  Advanced options:")
        label.setStyleSheet("""font-size: 16px;""")
        label.setMinimumWidth(150)


        title_layout = QtWidgets.QHBoxLayout()
        title_layout.addWidget(label, 1)
        title_layout.setSpacing(16)

        options_layout = QtWidgets.QGridLayout()
        options_layout.setColumnMinimumWidth(0, 16)
        options_layout.setColumnMinimumWidth(1, 54)
        options_layout.setColumnStretch(3, 1)
        options_layout.setHorizontalSpacing(32)
        options_layout.setVerticalSpacing(8)
        row = 0

        name = QtWidgets.QLabel("Co-occurence threshold:")
        field = FloatPropertyLineEdit()
        description = QtWidgets.QLabel("Minimum distance threshold in kilometers.")
        description.setStyleSheet("QLabel { font-style: italic; }")
        options_layout.addWidget(name, row, 1)
        options_layout.addWidget(field, row, 2)
        options_layout.addWidget(description, row, 3)
        self.controls.co_ocurrence_threshold = field
        row += 1

        name = QtWidgets.QLabel("Morphometrics alpha:")
        field = FloatPropertyLineEdit()
        description = QtWidgets.QLabel("Significance threshold for corrected p-values.")
        description.setStyleSheet("QLabel { font-style: italic; }")
        options_layout.addWidget(name, row, 1)
        options_layout.addWidget(field, row, 2)
        options_layout.addWidget(description, row, 3)
        self.controls.morphometrics_threshold = field
        row += 1

        self.addLayout(title_layout)
        self.addLayout(options_layout)


class ModeSelector(Card):
    valueChanged = QtCore.Signal(SubstitutionModel)

    def __init__(self, text, parent=None):
        super().__init__(parent)

        label = QtWidgets.QLabel(text + ":")
        label.setStyleSheet("""font-size: 16px;""")
        label.setMinimumWidth(150)

        spart = QtWidgets.QRadioButton("Directly from SPART XML")
        asapy = QtWidgets.QRadioButton("Use ASAP on a FASTA file")

        group = RadioButtonGroup()
        group.valueChanged.connect(self.valueChanged)
        group.add(spart, False)
        group.add(asapy, True)

        layout = QtWidgets.QHBoxLayout()
        layout.addWidget(label)
        layout.addWidget(spart)
        layout.addWidget(asapy, 1)
        layout.setSpacing(16)
        self.addLayout(layout)

        self.controls.group = group

    def setValue(self, value: SubstitutionModel):
        self.controls.group.setValue(value)


class AsapyComboboxDelegate(QtWidgets.QStyledItemDelegate):
    def paint(self, painter, option, index):
        if not index.isValid():
            return

        self.initStyleOption(option, index)
        option.text = index.data(AsapyCombobox.LabelRole)
        QtWidgets.QApplication.style().drawControl(QtWidgets.QStyle.CE_ItemViewItem, option, painter)

    def sizeHint(self, option, index):
        height = self.parent().sizeHint().height()
        return QtCore.QSize(300, height)


class AsapyCombobox(NoWheelComboBox):
    valueChanged = QtCore.Signal(SubstitutionModel)

    DisplayRole = QtCore.Qt.DisplayRole
    DataRole = QtCore.Qt.UserRole
    LabelRole = QtCore.Qt.UserRole + 1

    def __init__(self, models: list[SubstitutionModel] = list(SubstitutionModel), *args, **kwargs):
        super().__init__(*args, **kwargs)
        model = QtGui.QStandardItemModel()
        for enum in models:
            item = QtGui.QStandardItem()
            item.setData(enum.label, self.DisplayRole)
            item.setData(enum.description, self.LabelRole)
            item.setData(enum, self.DataRole)
            model.appendRow(item)
        self.setModel(model)

        delegate = AsapyComboboxDelegate(self)
        self.setItemDelegate(delegate)

        metrics = self.fontMetrics()
        length = max([metrics.horizontalAdvance(enum.description) for enum in SubstitutionModel])
        self.view().setMinimumWidth(length + 16)

        self.currentIndexChanged.connect(self._handle_index_changed)

    def _handle_index_changed(self, index):
        self.valueChanged.emit(self.itemData(index, self.DataRole))

    def setValue(self, value):
        index = self.findData(value, self.DataRole)
        self.setCurrentIndex(index)


class AsapSelector(PathFileSelector):
    def __init__(self, text, parent=None):
        super().__init__(text, parent)
        self.draw_options()

    def draw_options(self):
        layout = QtWidgets.QGridLayout()
        layout.setColumnMinimumWidth(0, 16)
        layout.setColumnMinimumWidth(1, 54)
        layout.setColumnStretch(3, 1)
        layout.setHorizontalSpacing(32)
        layout.setVerticalSpacing(8)
        row = 0

        name = QtWidgets.QLabel("Number of best scores:")
        field = IntPropertyLineEdit()
        description = QtWidgets.QLabel("Number of results with the highest scores to be displayed.")
        description.setStyleSheet("QLabel { font-style: italic; }")
        layout.addWidget(name, row, 1)
        layout.addWidget(field, row, 2)
        layout.addWidget(description, row, 3)
        self.controls.number = field
        row += 1

        name = QtWidgets.QLabel("Sequence length:")
        field = IntPropertyLineEdit()
        description = QtWidgets.QLabel("Original length of the sequence.")
        description.setStyleSheet("QLabel { font-style: italic; }")
        layout.addWidget(name, row, 1)
        layout.addWidget(field, row, 2)
        layout.addWidget(description, row, 3)
        self.controls.sequence_length = field
        row += 1

        name = QtWidgets.QLabel("Probability:")
        field = FloatPropertyLineEdit()
        description = QtWidgets.QLabel("Limit for results to be reported.")
        description.setStyleSheet("QLabel { font-style: italic; }")
        layout.addWidget(name, row, 1)
        layout.addWidget(field, row, 2)
        layout.addWidget(description, row, 3)
        self.controls.seuil_pvalue = field
        row += 1

        name = QtWidgets.QLabel("Seed:")
        field = IntPropertyLineEdit()
        description = QtWidgets.QLabel("Use fixed seed value. If you don’t want to use a fixed seed value, set to -1.")
        description.setStyleSheet("QLabel { font-style: italic; }")
        layout.addWidget(name, row, 1)
        layout.addWidget(field, row, 2)
        layout.addWidget(description, row, 3)
        self.controls.seed = field
        row += 1

        name = QtWidgets.QLabel("Model:")
        field = AsapyCombobox()
        description = QtWidgets.QLabel("Substitution model for distance computation.")
        description.setStyleSheet("QLabel { font-style: italic; }")
        layout.addWidget(name, row, 1)
        layout.addWidget(field, row, 2)
        layout.addWidget(description, row, 3)
        self.controls.method = field
        row += 1

        name = QtWidgets.QLabel("Kimura TS/TV:")
        field = FloatPropertyLineEdit()
        description = QtWidgets.QLabel("Transition/transversion for Kimura 3-P distance.")
        description.setStyleSheet("QLabel { font-style: italic; }")
        layout.addWidget(name, row, 1)
        layout.addWidget(field, row, 2)
        layout.addWidget(description, row, 3)
        self.controls.kimura_rate = field
        row += 1

        self.addLayout(layout)


class View(BlastTaskView):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.draw_cards()

    def draw_cards(self):
        self.cards = AttrDict()
        self.cards.title = GraphicTitleCard(title, long_description, pixmap_medium.resource, self)
        self.cards.progress = ProgressCard(self)
        self.cards.mode = ModeSelector("\u25CF  Spartitions", self)
        self.cards.asapy = AsapSelector("\u25C0  ASAP Sequences", self)
        self.cards.subsets = PathFileSelector("\u25C0  Subsets", self)
        self.cards.output = PathFileOutSelector("\u25B6  Output", self)
        self.cards.coords = PathFileSelector("\u25E6  Coordinates", self)
        self.cards.morphometrics = PathFileSelector("\u25E6  Morphometrics", self)
        self.cards.sequences = BatchSequenceSelector("Haplotype Seqs")
        self.cards.options = OptionsSelector(self)

        self.cards.asapy.set_placeholder_text("FASTA file to be processed by ASAPy")
        self.cards.subsets.set_placeholder_text("SPART XML file describing all subsets")
        self.cards.output.set_placeholder_text("Resulting SPART XML file with concordance information")
        self.cards.coords.set_placeholder_text("SPART XML or Tabfile containing lat/lon coordinates")
        self.cards.morphometrics.set_placeholder_text("Tabfile containing morphometrics")
        self.cards.sequences.set_placeholder_text("Phased FASTA file containing allele sequences")

        self.cards.asapy.roll = VerticalRollAnimation(self.cards.asapy)
        self.cards.subsets.roll = VerticalRollAnimation(self.cards.subsets)

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
        self.binder.bind(object.progression, self.cards.progress.showProgress)

        self.binder.bind(object.properties.name, self.cards.title.setTitle)
        self.binder.bind(object.properties.busy, self.cards.progress.setVisible)

        self.binder.bind(object.properties.asapy_mode, self.cards.mode.setValue)
        self.binder.bind(self.cards.mode.valueChanged, object.properties.asapy_mode)

        self.binder.bind(object.properties.asapy_mode, self.cards.asapy.roll.setAnimatedVisible)
        self.binder.bind(object.properties.asapy_mode, self.cards.subsets.roll.setAnimatedVisible, lambda x: not x)

        self.binder.bind(object.properties.subset_path, self.cards.subsets.set_path)
        self.binder.bind(self.cards.subsets.selectedPath, object.properties.subset_path)

        self.binder.bind(object.asapy_options.properties.input_path, self.cards.asapy.set_path)
        self.binder.bind(self.cards.asapy.selectedPath, object.asapy_options.properties.input_path)

        self.binder.bind(object.properties.output_path, self.cards.output.set_path)
        self.binder.bind(self.cards.output.selectedPath, object.properties.output_path)

        self.binder.bind(object.properties.coord_path, self.cards.coords.set_path)
        self.binder.bind(self.cards.coords.selectedPath, object.properties.coord_path)

        self.binder.bind(object.properties.morphometrics_path, self.cards.morphometrics.set_path)
        self.binder.bind(self.cards.morphometrics.selectedPath, object.properties.morphometrics_path)

        self.cards.sequences.bind_batch_model(self.binder, object.sequence_paths)

        self.cards.options.controls.co_ocurrence_threshold.bind_property(object.properties.co_ocurrence_threshold)
        self.cards.options.controls.morphometrics_threshold.bind_property(object.properties.morphometrics_threshold)

        self.cards.asapy.controls.number.bind_property(object.asapy_options.properties.number)
        self.cards.asapy.controls.sequence_length.bind_property(object.asapy_options.properties.sequence_length)
        self.cards.asapy.controls.seuil_pvalue.bind_property(object.asapy_options.properties.seuil_pvalue)
        self.cards.asapy.controls.seed.bind_property(object.asapy_options.properties.seed)
        self.cards.asapy.controls.kimura_rate.bind_property(object.asapy_options.properties.kimura_rate)

        self.binder.bind(object.asapy_options.properties.method, self.cards.asapy.controls.method.setValue)
        self.binder.bind(self.cards.asapy.controls.method.valueChanged, object.asapy_options.properties.method)


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
