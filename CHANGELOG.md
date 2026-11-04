# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.1.0] - 2026-11-04

### Added

- GTK3/Cairo annotator for existing screenshots.
- Arrow, rectangle, ellipse, line, pencil, highlighter and text tools.
- Select tool to move and resize annotations after adding them.
- Undo/redo and delete selected.
- Open existing images, save as PNG, and run a configurable upload command.
- Blank launch state with disabled tools until an image is opened.
- Preferences dialog with General and Upload tabs.
- About dialog with website and author links.
- Symbolic icon theme and application icon.
- XFCE integration through `xfce4-screenshooter` custom actions.
- Unit tests for the geometry model.

### Notes

- Linux/X11 focused; region capture relies on `xfce4-screenshooter`.
- Uploads are opt-in and disabled by default.
- No Wayland, blur or step numbering yet.

[Unreleased]: https://github.com/arodu/gannotate/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/arodu/gannotate/releases/tag/v0.1.0
