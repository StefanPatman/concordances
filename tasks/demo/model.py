from pathlib import Path

from itaxotools.common.bindings import Property
from itaxotools.taxi_gui.model.tasks import SubtaskModel, TaskModel

from . import process, title


class Model(TaskModel):
    task_name = title

    spart_path = Property(Path, Path())
    sequence_path = Property(Path, Path())
    output_path = Property(Path, Path())

    def __init__(self, name=None):
        super().__init__(name)
        self.can_open = False
        self.can_save = False

        self.subtask_init = SubtaskModel(self, bind_busy=False)

        for handle in [
            self.properties.spart_path,
            self.properties.sequence_path,
            self.properties.output_path,
        ]:
            self.binder.bind(handle, self.checkReady)
        self.checkReady()

        self.subtask_init.start(process.initialize)

    def isReady(self):
        if self.spart_path == Path():
            return False
        if self.sequence_path == Path():
            return False
        if self.output_path == Path():
            return False
        return True

    def start(self):
        super().start()

        self.exec(
            process.execute,
            spart_path=self.spart_path,
            sequence_path=self.sequence_path,
            output_path=self.output_path,
        )
