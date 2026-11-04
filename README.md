# Gannotate

A lightweight screenshot annotator for Linux, built with GTK3 and Cairo.

Gannotate opens an existing capture, lets you add arrows, shapes and text, and
can hand it off to any upload command you configure.

## Features

- Arrow, rectangle, ellipse, line, pencil, highlighter and text.
- Color picker and line width.
- Select tool to move and resize annotations after adding them.
- Undo/redo and delete selected.
- Save as PNG or run a configurable upload command.
- Uploads are opt-in and disabled by default.
- Small dependency footprint: GTK3 + Cairo.

## Requirements

- Python 3.10+
- PyGObject, GTK3 and pycairo

Arch / Manjaro:

```sh
sudo pacman -S python-gobject gtk3 python-cairo
```

Debian / Ubuntu:

```sh
sudo apt install python3-gi gir1.2-gtk-3.0 python3-cairo
```

## Run from source

```sh
./bin/gannotate path/to/image.png
```

## Install

```sh
sudo make install                    # /usr/local
make install PREFIX="$HOME/.local"   # user install
```

If you install to `$HOME/.local`, make sure `$HOME/.local/bin` is in your
`PATH`.

Uninstall:

```sh
sudo make uninstall
```

## Use with XFCE

Create a custom action for `xfce4-screenshooter` with this command:

```
$HOME/labs/gannotate/bin/gannotate %f
```

After `make install`, use:

```
gannotate %f
```

Then capture a region and pick the action. `%f` is the captured image path.

## Keyboard shortcuts

| Key                    | Action                    |
|------------------------|---------------------------|
| Enter                  | Upload (if configured)    |
| Ctrl+S                 | Save as...                |
| Esc                    | Cancel                    |
| Ctrl+Z                 | Undo                      |
| Ctrl+Shift+Z / Ctrl+Y  | Redo                      |
| Delete                 | Delete selected annotation |

## Upload configuration

Open the menu (hamburger) and choose **Preferences**. Set an upload command
there.

- Empty by default: uploads are disabled and the Upload button is greyed out.
- `%f` is replaced by the image path. If `%f` is missing, the path is appended
  as the last argument.
- The command is split into arguments (no shell pipes), for example:

```
/home/you/.local/bin/share-to-imgur.sh %f
```

If the command fails, the image is saved to `~/Pictures/Screenshots` instead of
being lost. Configuration lives in `~/.config/gannotate/config.json`.

## Development

```sh
make test
```

Tests cover the pure geometry model (bounding boxes, hit-testing, move and
resize) and do not require a display.

## Project layout

```
bin/gannotate              launcher for the source tree
data/gannotate.desktop     desktop entry
src/gannotate/app.py       GTK window and interactions
src/gannotate/model.py     annotation geometry (pure, testable)
src/gannotate/render.py    Cairo rendering
src/gannotate/config.py    config file handling
src/gannotate/upload.py    upload command runner
src/gannotate/__main__.py  CLI entry point
```

## Screenshots

![Gannotate annotating a screenshot](docs/screenshots/main.png)

![Preferences](docs/screenshots/preferences.png)

## Credits

Created by [arodu](https://github.com/arodu).

Icons are based on Font Awesome Free 7.3.1 (CC BY 4.0). See
`THIRD_PARTY_NOTICES.md`.

## License

GNU General Public License v3.0 (GPL-3.0).
