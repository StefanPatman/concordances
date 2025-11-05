from PySide6 import QtWidgets

from pathlib import Path

from itaxotools.taxi_gui import app
from itaxotools.taxi_gui.view.tasks import TaskView

from .types import Results


class View(TaskView):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.view = QtWidgets.QGraphicsView()

        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(self.view, 1)
        layout.setSpacing(6)
        layout.setContentsMargins(0, 0, 0, 0)

        self.setLayout(layout)

    def setObject(self, object):
        self.object = object
        self.binder.unbind_all()

        self.binder.bind(object.notification, self.showNotification)
        self.binder.bind(object.report_results, self.report_results)

    def report_results(self, task_name: str, results: Results):
        print(results.individual_list)

    def open(self):
        filename, _ = QtWidgets.QFileDialog.getOpenFileName(
            parent=self.window(),
            caption=f"{app.config.title} - Open file",
        )
        if not filename:
            return
        self.object.open(Path(filename))
