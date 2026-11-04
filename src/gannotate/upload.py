"""Run a user-configured upload command."""

import os
import shlex
import subprocess


def build_argv(template, path):
    """Turn an upload command template into an argv list.

    %f is replaced by the image path. If no %f is present, the path is
    appended as the last argument.
    """
    template = os.path.expandvars(os.path.expanduser(template.strip()))
    if not template:
        return None
    try:
        argv = shlex.split(template)
    except ValueError:
        return None
    if not argv:
        return None
    if any("%f" in part for part in argv):
        return [part.replace("%f", path) for part in argv]
    return argv + [path]


def run_upload(template, path):
    argv = build_argv(template, path)
    if not argv:
        return 1
    try:
        return subprocess.run(argv, check=False).returncode
    except OSError:
        return 127
