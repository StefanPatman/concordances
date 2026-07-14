from PySide6 import QtCore, QtWidgets

from itaxotools.taxi_gui.view.tasks import TaskView


class View(TaskView):
    def __init__(self, parent=None):
        super().__init__(parent)

        label = QtWidgets.QLabel("Coming soon.")
        label.setAlignment(QtCore.Qt.AlignCenter)

        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(label)
        layout.setContentsMargins(0, 0, 0, 0)

        self.setLayout(layout)
