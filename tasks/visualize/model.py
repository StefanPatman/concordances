from pathlib import Path

from itaxotools.common.bindings import Property
from itaxotools.taxi_gui.threading import ReportDone
from . import process, title
from ..common.model import BlastTaskModel
from itaxotools.taxi_gui.model.tasks import SubtaskModel


class Model(BlastTaskModel):
    task_name = title

    concordance_path = Property(Path, Path())

    def __init__(self, name=None):
        super().__init__(name)
        self.can_open = True
        self.can_save = False
        self.can_start = False

        self.subtask_init = SubtaskModel(self, bind_busy=False)
        self.subtask_init.start(process.initialize)

    def isReady(self):
        return True

    def start(self):
        super().start()

        self.exec(
            process.execute,
            concordance_path=self.concordance_path,
        )

    def onDone(self, report: ReportDone):
        self.report_results.emit(self.task_name, report.result)
        self.busy = False

    def open(self, path: Path):
        self.concordance_path = path
        self.start()
