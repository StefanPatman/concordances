from __future__ import annotations

from PySide6 import QtCore

from dataclasses import dataclass, field
from pathlib import Path

from itaxotools.taxi_gui.model.tasks import SubtaskModel
from itaxotools.taxi_gui.threading import ReportDone

from . import process, title
from ..common.model import BlastTaskModel
from .types import DocumentData, SaveResults, SpartitionData, SubsetData


class DoneSubtaskModel(SubtaskModel):
    task_name = "SpartitionerSubtask"

    done = QtCore.Signal(object)

    def onDone(self, report: ReportDone):
        self.done.emit(report)
        self.busy = False


@dataclass
class Subset:
    label: str
    individuals: list[str] = field(default_factory=list)


@dataclass
class Spartition:
    label: str
    subsets: list[Subset] = field(default_factory=list)
    original: dict | None = None
    dirty: bool = False

    def subset_of(self, individual: str) -> int | None:
        for index, subset in enumerate(self.subsets):
            if individual in subset.individuals:
                return index
        return None

    def assigned(self) -> set[str]:
        return {name for subset in self.subsets for name in subset.individuals}


class Document(QtCore.QObject):
    """The individuals and spartitions being edited.

    This is the single source of truth: widgets never move items around by
    themselves, they ask the document and redraw when it signals a change.
    """

    individualsChanged = QtCore.Signal()
    spartitionsChanged = QtCore.Signal()
    currentChanged = QtCore.Signal()
    subsetsChanged = QtCore.Signal()
    modifiedChanged = QtCore.Signal(bool)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.individuals: list[str] = []
        self.spartitions: list[Spartition] = []
        self.extras: dict = {}
        self.current: int = -1
        self.modified = False

    def set_modified(self, modified: bool):
        if self.modified == modified:
            return
        self.modified = modified
        self.modifiedChanged.emit(modified)

    def get_current(self) -> Spartition | None:
        if 0 <= self.current < len(self.spartitions):
            return self.spartitions[self.current]
        return None

    def load(self, data: DocumentData):
        self.individuals = list(data.individuals)
        self.spartitions = [
            Spartition(
                spartition.label,
                [
                    Subset(subset.label, list(subset.individuals))
                    for subset in spartition.subsets
                ],
                spartition.original,
                spartition.dirty,
            )
            for spartition in data.spartitions
        ]
        self.extras = data.extras
        self.current = 0 if self.spartitions else -1
        self.set_modified(False)
        self.individualsChanged.emit()
        self.spartitionsChanged.emit()
        self.currentChanged.emit()

    def dump(self) -> DocumentData:
        return DocumentData(
            list(self.individuals),
            [
                SpartitionData(
                    spartition.label,
                    [
                        SubsetData(subset.label, list(subset.individuals))
                        for subset in spartition.subsets
                    ],
                    spartition.original,
                    spartition.dirty,
                )
                for spartition in self.spartitions
            ],
            self.extras,
        )

    def reset(self):
        self.load(DocumentData([], [], {}))

    # Individuals

    def get_assigned_anywhere(self, individuals: list[str]) -> list[str]:
        assigned = set()
        for spartition in self.spartitions:
            assigned |= spartition.assigned()
        return [name for name in individuals if name in assigned]

    def set_individuals(self, individuals: list[str]):
        if individuals == self.individuals:
            return
        kept = set(individuals)
        for spartition in self.spartitions:
            for subset in spartition.subsets:
                remaining = [name for name in subset.individuals if name in kept]
                if len(remaining) != len(subset.individuals):
                    subset.individuals = remaining
                    spartition.dirty = True
        self.individuals = list(individuals)
        self.set_modified(True)
        self.individualsChanged.emit()
        self.subsetsChanged.emit()

    # Spartitions

    def get_spartition_labels(self) -> list[str]:
        return [spartition.label for spartition in self.spartitions]

    def suggest_spartition_label(self) -> str:
        labels = set(self.get_spartition_labels())
        number = len(self.spartitions) + 1
        while f"spartition_{number}" in labels:
            number += 1
        return f"spartition_{number}"

    def check_spartition_label(self, label: str, ignore: int = -1):
        if not label:
            raise ValueError("The spartition name cannot be empty.")
        for index, spartition in enumerate(self.spartitions):
            if index != ignore and spartition.label == label:
                raise ValueError(f"A spartition named {repr(label)} already exists.")

    def set_current(self, index: int):
        if index == self.current:
            return
        if not -1 <= index < len(self.spartitions):
            return
        self.current = index
        self.currentChanged.emit()

    def add_spartition(self, label: str):
        self.check_spartition_label(label)
        self.spartitions.append(Spartition(label, dirty=True))
        self.current = len(self.spartitions) - 1
        self.set_modified(True)
        self.spartitionsChanged.emit()
        self.currentChanged.emit()

    def rename_spartition(self, label: str):
        spartition = self.get_current()
        if spartition is None or spartition.label == label:
            return
        self.check_spartition_label(label, ignore=self.current)
        spartition.label = label
        self.set_modified(True)
        self.spartitionsChanged.emit()

    def delete_spartition(self):
        if self.get_current() is None:
            return
        del self.spartitions[self.current]
        self.current = min(self.current, len(self.spartitions) - 1)
        self.set_modified(True)
        self.spartitionsChanged.emit()
        self.currentChanged.emit()

    # Subsets of the current spartition

    def suggest_subset_label(self) -> str:
        spartition = self.get_current()
        labels = {subset.label for subset in spartition.subsets}
        number = len(spartition.subsets) + 1
        while str(number) in labels:
            number += 1
        return str(number)

    def check_subset_label(self, label: str, ignore: int = -1):
        if not label:
            raise ValueError("The subset name cannot be empty.")
        for index, subset in enumerate(self.get_current().subsets):
            if index != ignore and subset.label == label:
                raise ValueError(f"A subset named {repr(label)} already exists.")

    def _touch(self):
        self.get_current().dirty = True
        self.set_modified(True)
        self.subsetsChanged.emit()

    def add_subset(self, label: str | None = None) -> int | None:
        spartition = self.get_current()
        if spartition is None:
            return None
        if label is None:
            label = self.suggest_subset_label()
        self.check_subset_label(label)
        spartition.subsets.append(Subset(label))
        self._touch()
        return len(spartition.subsets) - 1

    def rename_subset(self, index: int, label: str):
        subset = self.get_current().subsets[index]
        if subset.label == label:
            return
        self.check_subset_label(label, ignore=index)
        subset.label = label
        self._touch()

    def delete_subset(self, index: int):
        del self.get_current().subsets[index]
        self._touch()

    def assign(self, individuals: list[str], index: int):
        """Move the individuals into the given subset, from wherever they were."""
        spartition = self.get_current()
        if spartition is None:
            return
        known = set(self.individuals)
        chosen = [name for name in individuals if name in known]
        if not chosen:
            return
        moving = set(chosen)
        target = spartition.subsets[index]
        for subset in spartition.subsets:
            if subset is not target:
                subset.individuals = [
                    name for name in subset.individuals if name not in moving
                ]
        present = set(target.individuals)
        target.individuals += [name for name in chosen if name not in present]
        self._touch()

    def unassign(self, individuals: list[str]):
        spartition = self.get_current()
        if spartition is None:
            return
        leaving = set(individuals)
        if not leaving & spartition.assigned():
            return
        for subset in spartition.subsets:
            subset.individuals = [
                name for name in subset.individuals if name not in leaving
            ]
        self._touch()

    def get_unassigned_counts(self) -> dict[str, int]:
        """How many individuals are left out of each spartition, if any."""
        counts = {}
        for spartition in self.spartitions:
            count = len(set(self.individuals) - spartition.assigned())
            if count:
                counts[spartition.label] = count
        return counts


class Model(BlastTaskModel):
    task_name = title

    report_saved = QtCore.Signal(object)
    report_imported = QtCore.Signal(list)

    def __init__(self, name=None):
        super().__init__(name)
        self.can_open = True
        self.can_save = True
        self.show_save = True
        self.can_start = False

        self.document = Document(self)
        self.has_draft = False

        self.subtask_init = SubtaskModel(self, bind_busy=False)
        self.subtask_init.start(process.initialize)

        self.subtask_open = DoneSubtaskModel(self, bind_busy=True)
        self.binder.bind(self.subtask_open.done, self._handle_open_done)

        self.subtask_import = DoneSubtaskModel(self, bind_busy=True)
        self.binder.bind(self.subtask_import.done, self._handle_import_done)

        self.subtask_save = DoneSubtaskModel(self, bind_busy=True)
        self.binder.bind(self.subtask_save.done, self._handle_save_done)

        self.document.individualsChanged.connect(self.check_done)

    def isReady(self):
        return True

    def checkRunnable(self):
        # Nothing to run: everything happens through open and save.
        self.can_start = False

    def check_done(self):
        """The toolbar only allows saving and clearing a task that is done,
        which here means that there is anything at all to save or clear."""
        self.done = bool(self.document.individuals) or self.has_draft

    def set_draft(self, has_draft: bool):
        """Whether individuals were typed in that the document has not seen yet."""
        self.has_draft = has_draft
        self.check_done()

    def open(self, path: Path):
        self.subtask_open.start(process.open_spart, path)

    def import_individuals(self, path: Path):
        self.subtask_import.start(process.import_individuals, path)

    def save(self, path: Path):
        self.subtask_save.start(process.save_spart, path, self.document.dump())

    def clear(self):
        self.document.reset()
        self.set_draft(False)

    def _handle_open_done(self, report: ReportDone):
        self.document.load(report.result)

    def _handle_import_done(self, report: ReportDone):
        self.report_imported.emit(report.result)

    def _handle_save_done(self, report: ReportDone):
        results: SaveResults = report.result
        self.document.set_modified(False)
        self.report_saved.emit(results)
