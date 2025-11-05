from PySide6 import QtCore, QtWidgets, QtGui

from pathlib import Path

from itaxotools.taxi_gui import app
from itaxotools.taxi_gui.view.tasks import TaskView

from .types import Results


class Visualizer(QtWidgets.QGraphicsView):
    def __init__(self, parent=None):
        super().__init__(parent)

        self._scene = QtWidgets.QGraphicsScene(self)
        self.setScene(self._scene)

        self.setRenderHint(QtGui.QPainter.Antialiasing)
        self.setMinimumSize(300, 300)

        self._palette = {}

    def _get_color_for_group(self, group: str) -> QtGui.QColor:
        if not hasattr(self, "_color_list"):
            self._color_list = [
                QtGui.QColor("#e6194b"),  # red
                QtGui.QColor("#3cb44b"),  # green
                QtGui.QColor("#ffe119"),  # yellow
                QtGui.QColor("#4363d8"),  # blue
                QtGui.QColor("#f58231"),  # orange
                QtGui.QColor("#911eb4"),  # purple
                QtGui.QColor("#46f0f0"),  # cyan
                QtGui.QColor("#f032e6"),  # magenta
                QtGui.QColor("#bcf60c"),  # lime
                QtGui.QColor("#fabebe"),  # pink
                QtGui.QColor("#008080"),  # teal
                QtGui.QColor("#e6beff"),  # lavender
                QtGui.QColor("#9a6324"),  # brown
                QtGui.QColor("#fffac8"),  # beige
                QtGui.QColor("#800000"),  # maroon
                QtGui.QColor("#aaffc3"),  # mint
                QtGui.QColor("#808000"),  # olive
                QtGui.QColor("#ffd8b1"),  # apricot
                QtGui.QColor("#000075"),  # navy
                QtGui.QColor("#808080"),  # gray
            ]

        if group not in self._palette:
            index = len(self._palette) % len(self._color_list)
            self._palette[group] = self._color_list[index]

        return self._palette[group]

    def set_data(self, individuals: dict[str, str], scores: dict[str, float | bool]):
        self._scene.clear()
        self._palette.clear()

        x, y = 0, 0
        y_step = 24
        individual_label_items = []
        score_label_items = []
        score_value_items = []

        for name, group in individuals.items():
            label_item = QtWidgets.QGraphicsTextItem(f"{name}")
            label_item.setPos(x, y)
            self._scene.addItem(label_item)
            individual_label_items.append((label_item, group))
            y += y_step

        if individual_label_items:
            rightmost = max(
                item.boundingRect().right() + item.x()
                for item, _ in individual_label_items
            )
        else:
            rightmost = 0

        padding_x = 40
        padding_y = 30
        col_x = rightmost + padding_x
        col_width = 40
        col_height = y

        y = 0
        for _, group in individual_label_items:
            color = self._get_color_for_group(group)
            segment_rect = QtCore.QRectF(col_x, y, col_width, y_step)
            self._scene.addRect(segment_rect, QtCore.Qt.NoPen, QtGui.QBrush(color))
            y += y_step

        outline_rect = QtCore.QRectF(col_x, 0, col_width, col_height)
        self._scene.addRect(
            outline_rect, QtGui.QPen(QtCore.Qt.black, 1), QtCore.Qt.NoBrush
        )

        col_x = rightmost + padding_x
        y = -y_step - padding_y
        for score, value in reversed(scores.items()):
            label_item = QtWidgets.QGraphicsTextItem(f"{score}")
            label_item.setPos(0, y)
            self._scene.addItem(label_item)
            score_label_items.append(label_item)

            if isinstance(value, float):
                value_item = QtWidgets.QGraphicsTextItem(f"{value:.2f}")
            elif isinstance(value, bool):
                value_item = QtWidgets.QGraphicsTextItem(
                    "\u2713" if value else "\u2717"
                )
            else:
                value_item = QtWidgets.QGraphicsTextItem("-")

            text_rect = value_item.boundingRect()
            value_item.setPos(col_x + col_width / 2 - text_rect.center().x(), y)

            self._scene.addItem(value_item)
            score_value_items.append(value_item)

            y -= y_step

        self._scene.setSceneRect(self._scene.itemsBoundingRect())


class View(TaskView):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.viz = Visualizer()

        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(self.viz, 1)
        layout.setSpacing(6)
        layout.setContentsMargins(0, 0, 0, 0)

        self.setLayout(layout)

    def setObject(self, object):
        self.object = object
        self.binder.unbind_all()

        self.binder.bind(object.notification, self.showNotification)
        self.binder.bind(object.report_results, self.report_results)

    def report_results(self, task_name: str, results: Results):
        for spartition in results.subset_table:
            data = results.subset_table[spartition]
            scores = results.score_table[spartition]
            self.viz.set_data(data, scores)

    def open(self):
        filename, _ = QtWidgets.QFileDialog.getOpenFileName(
            parent=self.window(),
            caption=f"{app.config.title} - Open file",
        )
        if not filename:
            return
        self.object.open(Path(filename))
