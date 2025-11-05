from PySide6 import QtCore, QtWidgets, QtGui

from pathlib import Path

from itaxotools.taxi_gui import app
from itaxotools.taxi_gui.view.tasks import TaskView

from .types import Results


class InstantTooltipTextItem(QtWidgets.QGraphicsTextItem):
    def __init__(self, text: str, tooltip: str, font: QtGui.QFont, parent=None):
        super().__init__(text, parent)
        self.setFont(font)
        self.setToolTip(tooltip)
        self.setAcceptHoverEvents(True)

    def hoverEnterEvent(self, event: QtWidgets.QGraphicsSceneHoverEvent):
        QtWidgets.QToolTip.showText(event.screenPos(), self.toolTip())
        super().hoverEnterEvent(event)


class RowOverlay(QtWidgets.QGraphicsRectItem):
    def __init__(self, rect, parent=None):
        super().__init__(rect, parent)
        self.setBrush(QtGui.QBrush(QtGui.QColor(0, 0, 0, 0)))
        self.setPen(QtCore.Qt.NoPen)
        self.setAcceptHoverEvents(True)

    def hoverEnterEvent(self, event):
        self.setBrush(QtGui.QBrush(QtGui.QColor(0, 0, 0, 50)))
        self.setPen(QtCore.Qt.NoPen)
        super().hoverEnterEvent(event)

    def hoverLeaveEvent(self, event):
        self.setBrush(QtGui.QBrush(QtGui.QColor(0, 0, 0, 0)))
        self.setPen(QtCore.Qt.NoPen)
        super().hoverLeaveEvent(event)


class Visualizer(QtWidgets.QGraphicsView):
    _color_list = [
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

    def __init__(self, parent=None):
        super().__init__(parent)

        self._scene = QtWidgets.QGraphicsScene(self)
        self.setScene(self._scene)

        self.setRenderHint(QtGui.QPainter.Antialiasing)
        self.setMinimumSize(500, 400)

        self._palette = {}
        self._font = QtGui.QFont("Arial", 10)  # private font

        self.y_step = 24
        self.padding_x = 40
        self.padding_y = 30
        self.col_width = 60
        self.col_spacing = 20

    def _get_color_for_group(self, group: str) -> QtGui.QColor:
        if group not in self._palette:
            index = len(self._palette) % len(self._color_list)
            self._palette[group] = self._color_list[index]
        return self._palette[group]

    def _draw_individual_list(self, individuals: list[str]):
        y = 0
        individual_label_items = []

        self._palette.clear()

        for name in individuals:
            label_item = QtWidgets.QGraphicsTextItem(name)
            label_item.setFont(self._font)
            label_item.setPos(0, y)
            self._scene.addItem(label_item)
            individual_label_items.append(label_item)

            y += self.y_step

    def _draw_spartition_column(
        self, col_x: float, individuals: list[str], subset: dict[str, str]
    ):
        self._palette.clear()
        y = 0

        for name in individuals:
            group = subset.get(name, "Unknown")
            color = self._get_color_for_group(group)
            rect = QtCore.QRectF(col_x, y, self.col_width, self.y_step)
            self._scene.addRect(rect, QtCore.Qt.NoPen, QtGui.QBrush(color))

            y += self.y_step

        outline_rect = QtCore.QRectF(col_x, 0, self.col_width, y)
        self._scene.addRect(
            outline_rect, QtGui.QPen(QtCore.Qt.black, 1), QtCore.Qt.NoBrush
        )

    def _draw_scores(self, col_x: float, top_y: float, scores: dict[str, float | bool]):
        y = -self.y_step - self.padding_y
        score_label_items = []
        score_value_items = []

        for score, value in reversed(scores.items()):
            label_item = QtWidgets.QGraphicsTextItem(score)
            label_item.setFont(self._font)
            label_item.setPos(0, y)
            self._scene.addItem(label_item)
            score_label_items.append(label_item)

            if isinstance(value, float):
                value_item = QtWidgets.QGraphicsTextItem(f"{value:.3f}")
            elif isinstance(value, int):
                value_item = QtWidgets.QGraphicsTextItem(str(value))
            elif isinstance(value, bool):
                value_item = QtWidgets.QGraphicsTextItem(
                    "\u2713" if value else "\u2717"
                )
                font = value_item.font()
                font.setBold(True)
                font.setPointSize(14)
                value_item.setFont(font)
            else:
                value_item = QtWidgets.QGraphicsTextItem("-")
            value_item.setFont(self._font)

            text_rect = value_item.boundingRect()
            value_item.setPos(col_x + self.col_width / 2 - text_rect.center().x(), y)
            self._scene.addItem(value_item)
            score_value_items.append(value_item)

            y -= self.y_step

        return y

    def _draw_column_title(self, col_x: float, y: float, title: str, index: int):
        display_letter = chr(ord("A") + index)
        font = QtGui.QFont(self._font)
        font.setPointSize(self._font.pointSize() + 4)
        title_item = InstantTooltipTextItem(display_letter, title, font)

        text_rect = title_item.boundingRect()
        title_item.setPos(
            col_x + self.col_width / 2 - text_rect.center().x(), y - self.padding_y
        )
        self._scene.addItem(title_item)

    def _add_row_hover_overlays(self, individual_list: list[str], total_width: float):
        for row_index, _ in enumerate(individual_list):
            rect = QtCore.QRectF(0, row_index * self.y_step, total_width, self.y_step)
            overlay = RowOverlay(rect)

            self._scene.addItem(overlay)

    def set_data(
        self,
        individual_list: list[str],
        subset_table: dict[str, dict[str, str]],
        score_table: dict[str, dict[str, float | bool]],
    ):
        self._scene.clear()

        font_metrics = QtGui.QFontMetrics(self._font)
        max_name_width = max(
            font_metrics.horizontalAdvance(name) for name in individual_list
        )
        col_x = max_name_width + self.padding_x

        self._draw_individual_list(individual_list)
        total_overlay_width = col_x + len(subset_table) * (
            self.col_width + self.col_spacing
        )
        self._add_row_hover_overlays(individual_list, total_overlay_width)

        for index, spartition in enumerate(subset_table):
            subset = subset_table[spartition]
            scores = score_table.get(spartition, {})

            self._draw_spartition_column(col_x, individual_list, subset)
            y = self._draw_scores(col_x, 0, scores)
            self._draw_column_title(col_x, y, spartition, index)

            col_x += self.col_width + self.col_spacing

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
        self.viz.set_data(
            results.individual_list,
            results.subset_table,
            results.score_table,
        )

    def open(self):
        filename, _ = QtWidgets.QFileDialog.getOpenFileName(
            parent=self.window(),
            caption=f"{app.config.title} - Open file",
        )
        if not filename:
            return
        self.object.open(Path(filename))
