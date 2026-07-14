from . import title
from ..common.model import BlastTaskModel


class Model(BlastTaskModel):
    task_name = title

    def __init__(self, name=None):
        super().__init__(name)
        self.can_open = False
        self.can_save = False
        self.can_start = False

    def isReady(self):
        return False
