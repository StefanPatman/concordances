from PySide6 import QtCore
from pathlib import Path

from itaxotools.common.bindings import Property
from itaxotools.taxi_gui.model.tasks import SubtaskModel
from itaxotools.taxi_gui.threading import ReportDone
from . import process, title
from ..common.model import BlastTaskModel
from .types import OpenResults


class VersionSubtaskModel(SubtaskModel):
    task_name = "OpenSubtask"

    done = QtCore.Signal(OpenResults)

    def onDone(self, results: OpenResults):
        self.done.emit(results)
        self.busy = False


class Model(BlastTaskModel):
    task_name = title

    concordance_path = Property(Path, Path())
    output_path = Property(Path, Path())

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

    def _handle_open_results(self, results: OpenResults):
        # Update a table model with results
        pass

    def isReady(self):
        if self.concordance_path == Path():
            return False
        if self.output_path == Path():
            return False
        return True

    def start(self):
        super().start()

        self.exec(
            process.execute,
            concordance_path=self.concordance_path,
            output_path=self.output_path,
        )

    def onDone(self, report: ReportDone):
        self.report_results.emit(self.task_name, report.result)
        self.busy = False

    def open(self, path: Path):
        self.concordance_path = path
        self.output_path = path.with_stem(path.stem + "_scored")
        self.subtask_open.start(process.open_spart, path)
