from PySide6 import QtCore, QtGui

from enum import Enum
from pathlib import Path
from typing import Iterator

from itaxotools.common.widgets import VectorPixmap
from itaxotools.taxi_gui.app import skin
from itaxotools.taxi_gui.app.resources import LazyResourceCollection


class Size(Enum):
    Large = QtCore.QSize(128, 128)
    Medium = QtCore.QSize(64, 64)
    Small = QtCore.QSize(16, 16)

    def __init__(self, size):
        self.size = size


def get_data(path: str):
    here = Path(__file__).parent
    return str(here / path)


def text_from_path(path) -> str:
    with open(path, "r") as file:
        return file.read()


def lines_from_path(path) -> Iterator[str]:
    for line in open(path).readlines():
        yield line


icons = LazyResourceCollection(
    pilot=lambda: QtGui.QIcon(get_data("logos/pilot.ico")),
)


pixmaps = LazyResourceCollection(
    pilot=lambda: VectorPixmap(
        get_data("logos/pilot_banner.svg"),
        size=QtCore.QSize(170, 48),
        colormap=skin.colormap_icon,
    ),
)


task_pixmaps_large = LazyResourceCollection(
    about=lambda: VectorPixmap(get_data("graphics/about.svg"), Size.Large.size),
)


task_pixmaps_medium = LazyResourceCollection(
    about=lambda: VectorPixmap(get_data("graphics/about.svg"), Size.Medium.size),
)
