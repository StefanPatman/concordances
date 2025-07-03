from pathlib import Path

from itaxotools.common.bindings import Property
from itaxotools.taxi_gui.model.tasks import SubtaskModel, TaskModel

from . import process, title


class Model(TaskModel):
    task_name = title

    subset_path = Property(Path, Path())
    output_path = Property(Path, Path())
    coord_path = Property(Path, Path())
    sequence_path = Property(Path, Path())
    morphometrics_path = Property(Path, Path())

    def __init__(self, name=None):
        super().__init__(name)
        self.can_open = False
        self.can_save = False

        self.subtask_init = SubtaskModel(self, bind_busy=False)

        for handle in [
            self.properties.subset_path,
            self.properties.output_path,
            self.properties.coord_path,
            self.properties.sequence_path,
            self.properties.morphometrics_path,
        ]:
            self.binder.bind(handle, self.checkReady)
        self.checkReady()

        self.subtask_init.start(process.initialize)

    def isReady(self):
        if self.subset_path == Path():
            return False
        if self.output_path == Path():
            return False
        if not any((
            self.coord_path != Path(),
            self.sequence_path != Path(),
            self.morphometrics_path != Path(),
        )):
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
            sequence_path=self.path_or_none(self.sequence_path),
            morphometrics_path=self.path_or_none(self.morphometrics_path),
        )
