"""Gannotate - a lightweight GTK3 screenshot annotator."""

from importlib.resources import files

__version__ = "0.2.0"
__app_name__ = "Gannotate"

ICON_PATH = str(files(__name__).joinpath("data", "gannotate.png"))
ICON_ROOT = files(__name__).joinpath("data", "icons")
