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
from .types import SubstitutionModel
from ..common.model import BatchSequenceModel, BlastTaskModel


class AsapyOptions(Object):
    input_path = Property(Path, Path())
    number = Property(int, 10)
    sequence_length = Property(int, 600)
    seuil_pvalue = Property(float, 0.01)
    seed = Property(int, -1)
    method = Property(SubstitutionModel, SubstitutionModel.JC)
    kimura_rate = Property(float, 2.0)

    def as_dict(self) -> AttrDict:
        return AttrDict({p.key: p.value for p in self.properties})


class Model(BlastTaskModel):
    task_name = title

    asapy_mode = Property(bool, False)
    asapy_options = Property(AsapyOptions, Instance)

    subset_path = Property(Path, Path())
    output_path = Property(Path, Path())
    coord_path = Property(Path, Path())
    morphometrics_path = Property(Path, Path())
    sequence_paths = Property(BatchSequenceModel, Instance)

    co_ocurrence_threshold = Property(float, 5.0)
    morphometrics_threshold = Property(float, 0.05)

    def __init__(self, name=None):
        super().__init__(name)
        self.can_open = False
        self.can_save = False

        self.subtask_init = SubtaskModel(self, bind_busy=False)

        for handle in [
            self.properties.asapy_mode,
            self.asapy_options.properties.input_path,
            self.properties.subset_path,
            self.properties.output_path,
            self.properties.coord_path,
            self.properties.morphometrics_path,
            self.sequence_paths.properties.ready,
            self.properties.co_ocurrence_threshold,
            self.properties.morphometrics_threshold,
        ]:
            self.binder.bind(handle, self.checkReady)
        self.checkReady()

        self.subtask_init.start(process.initialize)

    def isReady(self):
        if self.asapy_mode and self.asapy_options.input_path == Path():
            return False
        if not self.asapy_mode and self.subset_path == Path():
            return False
        if self.output_path == Path():
            return False
        if not any((
            self.coord_path != Path(),
            self.morphometrics_path != Path(),
            self.sequence_paths.ready,
        )):
            return False
        if not self.co_ocurrence_threshold:
            return False
        if not self.morphometrics_threshold:
            return False
        return True

    @staticmethod
    def path_or_none(path: Path) -> Path | None:
        if path == Path():
            return None
        return path

    def start(self):
        super().start()

        self.exec(
            process.execute,
            subset_path=self.subset_path,
            output_path=self.output_path,
            coord_path=self.path_or_none(self.coord_path),
            morphometrics_path=self.path_or_none(self.morphometrics_path),
            sequence_paths=self.sequence_paths.get_all_paths(),
            co_ocurrence_threshold=self.co_ocurrence_threshold,
            morphometrics_threshold=self.morphometrics_threshold,
            asapy_mode=self.asapy_mode,
            asapy_options=self.asapy_options.as_dict(),
        )

    def onDone(self, report: ReportDone):
        self.report_results.emit(self.task_name, report.result)
        self.busy = False
        self.reset_asapy()

    def onFail(self, report: ReportFail):
        super().onFail(report)
        self.reset_asapy()

    def onError(self, report: ReportExit):
        super().onError(report)
        self.reset_asapy()

    def onStop(self, report: ReportStop):
        super().onStop(report)
        self.reset_asapy()

    def reset_asapy(self):
        if self.asapy_mode:
            self.worker.reset()

    def open(self, path: Path):
        self.subset_path = path
        self.output_path = path.with_stem(path.stem + "_concordances")
