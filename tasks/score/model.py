from pathlib import Path

from itaxotools.common.bindings import Property, Instance
from itaxotools.taxi_gui.model.tasks import SubtaskModel, TaskModel
from itaxotools.taxi_gui.model.common import Object
from itaxotools.taxi_gui.loop import ReportDone
from itaxotools.taxi_gui.types import Notification
from itaxotools.common.utility import AttrDict
from itaxotools.taxi_gui.threading import (
    ReportDone,
    ReportExit,
    ReportFail,
    ReportProgress,
    ReportStop,
    Worker,
)
from . import process, title
from ..common.model import BatchSequenceModel, BlastTaskModel


class Model(BlastTaskModel):
    task_name = title

    concordance_path = Property(Path, Path())
    output_path = Property(Path, Path())

    def __init__(self, name=None):
        super().__init__(name)
        self.can_open = False
        self.can_save = False

        self.subtask_init = SubtaskModel(self, bind_busy=False)

        for handle in [
            self.properties.concordance_path,
            self.properties.output_path,
        ]:
            self.binder.bind(handle, self.checkReady)
        self.checkReady()

        self.subtask_init.start(process.initialize)

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
