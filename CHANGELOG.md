# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.2.0] - 2026-11-07

### Added

- Copy the annotated image to the clipboard without closing the window
  (toolbar button, menu item and Ctrl+C), with a desktop notification.
- Upload option to keep the window open instead of closing it, with the
  result shown as a desktop notification.
- Debian `.deb` package build, with a CI workflow that attaches it to
  releases.
- Arch `PKGBUILD` for building the package and publishing it in the AUR.

## [0.1.0] - 2026-11-04

### Added

- GTK3/Cairo annotator for existing screenshots.
- Arrow, rectangle, ellipse, line, pencil, highlighter and text tools.
- Four arrow heads (classic, triangle, slim, wide), with icons in the
  Preferences selector.
- Select tool to move and resize annotations after adding them.
- Undo/redo and delete selected.
- Open existing images, save as PNG, and run a configurable upload command.
- Blank launch state with disabled tools until an image is opened.
- Preferences dialog with General and Upload tabs.
- About dialog with website and author links.
- Original symbolic icon set and application icon, with no third-party
  icon dependency.
- Resizable, scrollable canvas with zoom controls (Ctrl+scroll, +/-, Fit,
  1:1) and middle-drag or Ctrl+drag panning.
- XFCE integration through `xfce4-screenshooter` custom actions.
- Unit tests for the geometry model.
- UI tests for the main window.

### Changed

- Open Image now starts in the last folder, or `~/Pictures` when blank.

### Notes

- Linux/X11 focused; region capture relies on `xfce4-screenshooter`.
- Uploads are opt-in and disabled by default.
- No Wayland, blur or step numbering yet.

[Unreleased]: https://github.com/arodu/gannotate/compare/v0.2.0...HEAD
[0.2.0]: https://github.com/arodu/gannotate/releases/tag/v0.2.0
[0.1.0]: https://github.com/arodu/gannotate/releases/tag/v0.1.0
