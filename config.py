from resources import icons, pixmaps
from tasks import (
    shuffle,
    profile,
    score,
    visualize,
    review,
    spartitioner,
)

title = "Concordance Pilot"
icon = icons.pilot
pixmap = pixmaps.pilot

dashboard = "constrained"

show_open = True
show_save = False

tasks = [
    [profile, score, visualize],
    [shuffle, review, spartitioner],
]
