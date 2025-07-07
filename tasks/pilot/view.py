from PySide6 import QtCore, QtWidgets

from pathlib import Path

from itaxotools.common.utility import AttrDict
from itaxotools.taxi_gui import app
from itaxotools.taxi_gui.tasks.common.view import ProgressCard
from itaxotools.taxi_gui.view.animations import VerticalRollAnimation
from itaxotools.taxi_gui.view.cards import Card
from itaxotools.taxi_gui.view.widgets import GLineEdit, RadioButtonGroup

from ..common.view import (
    BlastTaskView,
    GraphicTitleCard,
    PathSelector,
    BatchSequenceSelector,
)
from ..common.widgets import IntPropertyLineEdit, PropertyLineEdit
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


class View(BlastTaskView):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.draw_cards()

    def draw_cards(self):
        self.cards = AttrDict()
        self.cards.title = GraphicTitleCard(title, long_description, pixmap_medium.resource, self)
        self.cards.progress = ProgressCard(self)
        self.cards.subsets = PathFileSelector("\u25C0  Subsets", self)
        self.cards.output = PathFileOutSelector("\u25B6  Output", self)
        self.cards.coords = PathFileSelector("\u25E6  Coordinates", self)
        self.cards.morphometrics = PathFileSelector("\u25E6  Morphometrics", self)
        self.cards.sequences = BatchSequenceSelector("Haplotype Seqs")

        self.cards.subsets.set_placeholder_text("SPART XML file describing all subsets")
        self.cards.output.set_placeholder_text("Resulting SPART XML file with concordance information")
        self.cards.coords.set_placeholder_text("SPART XML or Tabfile containing lat/lon coordinates")
        self.cards.morphometrics.set_placeholder_text("Tabfile containing morphometrics")
        self.cards.sequences.set_placeholder_text("Phased FASTA file containing allele sequences")

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

        self.binder.bind(object.properties.subset_path, self.cards.subsets.set_path)
        self.binder.bind(self.cards.subsets.selectedPath, object.properties.subset_path)

        self.binder.bind(object.properties.output_path, self.cards.output.set_path)
        self.binder.bind(self.cards.output.selectedPath, object.properties.output_path)

        self.binder.bind(object.properties.coord_path, self.cards.coords.set_path)
        self.binder.bind(self.cards.coords.selectedPath, object.properties.coord_path)

        self.binder.bind(object.properties.morphometrics_path, self.cards.morphometrics.set_path)
        self.binder.bind(self.cards.morphometrics.selectedPath, object.properties.morphometrics_path)

        self.cards.sequences.bind_batch_model(self.binder, object.sequence_paths)

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
