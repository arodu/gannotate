"""Desktop notifications."""

import os
import subprocess

from . import ICON_PATH, __app_name__


def notify(message, title=__app_name__, icon=None):
    if icon is None:
        icon = ICON_PATH if os.path.isfile(ICON_PATH) else "gannotate"
    try:
        subprocess.Popen(
            ["notify-send", "-a", __app_name__, "-i", str(icon), title, message],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except OSError:
        pass
