"""Command-line entry point for Gannotate."""

import os
import shutil
import subprocess
import sys
import time

import gi

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk  # noqa: E402

from . import ICON_PATH, __app_name__  # noqa: E402
from .app import Gannotate  # noqa: E402
from .config import load_config  # noqa: E402
from .upload import run_upload  # noqa: E402


def notify(message):
    icon = ICON_PATH if os.path.isfile(ICON_PATH) else "gannotate"
    subprocess.run(["notify-send", "-i", icon, __app_name__, message], check=False)


def save_local(path):
    shots = os.path.expanduser("~/Pictures/Screenshots")
    os.makedirs(shots, exist_ok=True)
    dest = os.path.join(shots, time.strftime("%Y%m%d-%H%M%S") + ".png")
    shutil.move(path, dest)
    return dest


def main(argv=None):
    argv = sys.argv if argv is None else argv
    if len(argv) != 2:
        print(f"usage: {argv[0]} <image>", file=sys.stderr)
        return 2
    path = argv[1]
    if not os.path.isfile(path):
        print(f"not found: {path}", file=sys.stderr)
        return 1

    config = load_config()
    app = Gannotate(path, config)
    Gtk.main()

    out = app.result_path
    if not out or not os.path.isfile(out) or not app.upload_after:
        return 0

    command = app.config.get("upload_command", "")
    if os.environ.get("ANNOTATE_NO_UPLOAD") == "1" or not command.strip():
        dest = save_local(out)
        notify(f"Screenshot saved: {dest}")
    elif run_upload(command, out) != 0:
        dest = save_local(out)
        notify(f"Upload failed; screenshot saved: {dest}")

    shutil.rmtree(os.path.dirname(out), ignore_errors=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
