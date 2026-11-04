"""Gannotate main window."""

import copy
import math
import os
import tempfile
import time

import cairo
import gi

gi.require_version("Gtk", "3.0")
gi.require_version("Gdk", "3.0")
from gi.repository import Gdk, GdkPixbuf, GLib, Gtk  # noqa: E402

from . import ICON_PATH, ICON_ROOT, __app_name__, __version__  # noqa: E402
from .config import save_config  # noqa: E402
from .model import bbox, hit, scale_annotation, translate  # noqa: E402
from .render import ARROW_STYLES, draw_annotation, flatten, measure_text  # noqa: E402

HANDLE = 9  # screen pixels
TOOLS = [
    ("select", "Select / move", "gannotate-select-symbolic"),
    ("arrow", "Arrow", "gannotate-arrow-symbolic"),
    ("rect", "Rectangle", "gannotate-rect-symbolic"),
    ("ellipse", "Ellipse", "gannotate-ellipse-symbolic"),
    ("line", "Line", "gannotate-line-symbolic"),
    ("pen", "Pencil", "gannotate-pen-symbolic"),
    ("mark", "Highlighter", "gannotate-highlighter-symbolic"),
    ("text", "Text", "gannotate-text-symbolic"),
]

ARROW_STYLE_LABELS = (
    ("classic", "Classic"),
    ("triangle", "Triangle"),
    ("slim", "Slim"),
    ("wide", "Wide"),
)

_TOOLBAR_CSS = b"""
.gannotate-toolbar {
    background-color: @theme_bg_color;
    border-bottom: 1px solid alpha(@theme_fg_color, 0.12);
}
.gannotate-toolbar button,
.gannotate-toolbar togglebutton {
    border: none;
    box-shadow: none;
    background: transparent;
    padding: 4px;
    min-width: 0;
    min-height: 0;
}
.gannotate-toolbar button:hover,
.gannotate-toolbar togglebutton:hover {
    background-color: alpha(@theme_fg_color, 0.10);
    border-radius: 4px;
}
.gannotate-toolbar togglebutton:checked {
    background-color: alpha(@theme_selected_bg_color, 0.35);
    border-radius: 4px;
}
.gannotate-toolbar colorbutton {
    min-width: 24px;
    min-height: 24px;
    padding: 0;
    border: none;
    box-shadow: none;
}
.gannotate-toolbar spinbutton {
    min-height: 24px;
    border: none;
    box-shadow: none;
    background: transparent;
}
.gannotate-statusbar {
    background-color: @theme_bg_color;
    border-top: 1px solid alpha(@theme_fg_color, 0.12);
}
.gannotate-statusbar button {
    border: none;
    box-shadow: none;
    background: transparent;
    padding: 2px 6px;
    min-width: 0;
    min-height: 0;
}
.gannotate-statusbar button:hover {
    background-color: alpha(@theme_fg_color, 0.10);
    border-radius: 4px;
}
"""
_css_installed = False


def _install_css():
    global _css_installed
    if _css_installed:
        return
    provider = Gtk.CssProvider()
    provider.load_from_data(_TOOLBAR_CSS)
    screen = Gdk.Screen.get_default()
    if screen is not None:
        Gtk.StyleContext.add_provider_for_screen(
            screen, provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )
        _css_installed = True


_icons_installed = False


def _install_icons():
    global _icons_installed
    if _icons_installed:
        return
    theme = Gtk.IconTheme.get_default()
    root = str(ICON_ROOT)
    if root not in theme.get_search_path():
        theme.append_search_path(root)
    _icons_installed = True


def _arrow_pixbuf(style, color, width=24, height=22):
    surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, width, height)
    cr = cairo.Context(surface)
    sample = {
        "type": "arrow",
        "p0": (2.0, height / 2),
        "p1": (width - 2.0, height / 2),
        "color": (color.red, color.green, color.blue),
        "width": 2.5,
    }
    draw_annotation(cr, sample, style)
    return Gdk.pixbuf_get_from_surface(surface, 0, 0, width, height)


class Gannotate(Gtk.Window):
    def __init__(self, path, config):
        GLib.set_prgname("gannotate")
        GLib.set_application_name(__app_name__)
        try:
            Gdk.set_program_class("Gannotate")
        except Exception:
            pass
        super().__init__(title=__app_name__)
        _install_css()
        _install_icons()
        try:
            Gtk.Window.set_default_icon_from_file(ICON_PATH)
            self.set_icon_from_file(ICON_PATH)
        except Exception:
            pass

        self.config = config
        self.upload_command = config.get("upload_command", "")

        if path is None:
            self.current_path = None
            self.pixbuf = None
            self.base_surface = None
            self.img_w = 0
            self.img_h = 0
            self.scale = 1.0
            dw, dh = 820, 520
            self.set_title(__app_name__)
        else:
            self.current_path = path
            dw, dh = self._set_image(GdkPixbuf.Pixbuf.new_from_file(path))
            self.set_title(f"{__app_name__} - {os.path.basename(path)}")

        self.annots = []
        self.history = []
        self.future = []
        self.current = None
        self.selected = None
        self.tool = "select"
        self.color = self._config_color(config.get("default_color"))
        self.width = self._config_width(config.get("default_width"))
        self.arrow_style = self._config_arrow_style(config.get("arrow_style"))
        self.result_path = None
        self.upload_after = False
        self.drag_mode = None
        self.drag_index = None
        self.drag_orig = None
        self.drag_start = None
        self.drag_anchor = None
        self.drag_corner = None
        self.pending_history = False
        self.tool_buttons = {}
        self.pan_start = None
        self.zoom_fit_mode = True
        self._fit_pending = False
        self._fallback_viewport = (820, 520)

        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self.add(vbox)

        bar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
        bar.set_border_width(5)
        bar.get_style_context().add_class("gannotate-toolbar")
        self.toolbar = bar
        vbox.pack_start(bar, False, False, 0)

        for key, label, icon in TOOLS:
            btn = Gtk.ToggleButton()
            btn.set_relief(Gtk.ReliefStyle.NONE)
            btn.set_image(Gtk.Image.new_from_icon_name(icon, Gtk.IconSize.BUTTON))
            btn.set_tooltip_text(label)
            btn.connect("toggled", self.on_tool, key)
            self.tool_buttons[key] = btn
            bar.pack_start(btn, False, False, 0)

        bar.pack_start(Gtk.Separator(orientation=Gtk.Orientation.VERTICAL), False, False, 4)

        self.color_btn = Gtk.ColorButton()
        self.color_btn.set_relief(Gtk.ReliefStyle.NONE)
        self.color_btn.set_size_request(24, 24)
        rgba = Gdk.RGBA()
        rgba.red, rgba.green, rgba.blue, rgba.alpha = *self.color, 1.0
        self.color_btn.set_rgba(rgba)
        self.color_btn.set_tooltip_text("Color")
        self.color_btn.connect("color-set", self.on_color)
        bar.pack_start(self.color_btn, False, False, 0)

        self.width_spin = Gtk.SpinButton.new_with_range(1, 30, 1)
        self.width_spin.set_value(self.width)
        self.width_spin.set_tooltip_text("Line width")
        self.width_spin.connect("value-changed", self.on_width)
        bar.pack_start(self.width_spin, False, False, 0)

        bar.pack_start(Gtk.Separator(orientation=Gtk.Orientation.VERTICAL), False, False, 4)
        self.undo_btn = self.icon_button(
            "gannotate-undo-symbolic", "Undo (Ctrl+Z)", self.undo
        )
        bar.pack_start(self.undo_btn, False, False, 0)
        self.redo_btn = self.icon_button(
            "gannotate-redo-symbolic", "Redo (Ctrl+Shift+Z)", self.redo_last
        )
        bar.pack_start(self.redo_btn, False, False, 0)

        bar.pack_end(self.menu_button(), False, False, 0)
        bar.pack_end(Gtk.Separator(orientation=Gtk.Orientation.VERTICAL), False, False, 4)
        self.save_btn = self.icon_button(
            "gannotate-save-symbolic", "Save as... (Ctrl+S)", self.save_dialog
        )
        bar.pack_end(self.save_btn, False, False, 0)
        self.upload_btn = self.icon_button("gannotate-upload-symbolic", "Upload (Enter)", self.upload)
        bar.pack_end(self.upload_btn, False, False, 0)

        self.area = Gtk.DrawingArea()
        self.area.set_size_request(dw, dh)
        self.area.set_halign(Gtk.Align.CENTER)
        self.area.set_valign(Gtk.Align.CENTER)
        self.area.add_events(
            Gdk.EventMask.BUTTON_PRESS_MASK
            | Gdk.EventMask.BUTTON_RELEASE_MASK
            | Gdk.EventMask.POINTER_MOTION_MASK
            | Gdk.EventMask.SCROLL_MASK
            | Gdk.EventMask.SMOOTH_SCROLL_MASK
        )
        self.area.connect("draw", self.on_draw)
        self.area.connect("button-press-event", self.on_press)
        self.area.connect("button-release-event", self.on_release)
        self.area.connect("motion-notify-event", self.on_motion)
        self.area.connect("scroll-event", self.on_scroll)

        self.scrolled = Gtk.ScrolledWindow()
        self.scrolled.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        self.scrolled.set_shadow_type(Gtk.ShadowType.NONE)
        self.scrolled.add(self.area)
        self.scrolled.connect("size-allocate", self.on_viewport_resize)
        self.hadj = self.scrolled.get_hadjustment()
        self.vadj = self.scrolled.get_vadjustment()
        vbox.pack_start(self.scrolled, True, True, 0)

        self.statusbar = self.build_statusbar()
        vbox.pack_start(self.statusbar, False, False, 0)

        self.connect("key-press-event", self.on_key)
        self.connect("destroy", Gtk.main_quit)

        if path is not None:
            target_w, target_h = self._default_window_size()
            self._fallback_viewport = (
                target_w,
                max(1, target_h - self._chrome_height()),
            )
            self.resize(target_w, target_h)
            self.zoom_fit()
        else:
            self.resize(820, 610)
        self.tool_buttons["select"].set_active(True)
        self.set_image_controls(path is not None)
        self.update_info_label()
        self.show_all()
        if path is not None:
            GLib.idle_add(self._fit_after_show)

    def build_statusbar(self):
        bar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        bar.set_border_width(4)
        bar.get_style_context().add_class("gannotate-statusbar")

        self.info_label = Gtk.Label(label="")
        self.info_label.set_xalign(0)
        self.info_label.set_tooltip_text("Ctrl+drag or middle-drag to pan")
        bar.pack_start(self.info_label, True, True, 0)

        self.zoom_out_btn = self._zoom_button(
            "\u2212", "Zoom out (Ctrl+-)", self.zoom_out
        )
        self.zoom_in_btn = self._zoom_button(
            "+", "Zoom in (Ctrl++)", self.zoom_in
        )
        self.zoom_label = Gtk.Label(label="\u2014")
        self.zoom_label.set_width_chars(5)
        fit_btn = self._zoom_button("Fit", "Fit to window (Ctrl+0)", self.zoom_fit)
        actual_btn = self._zoom_button("1:1", "Actual size (Ctrl+1)", self.zoom_actual)
        self.zoom_buttons = [
            self.zoom_out_btn,
            self.zoom_in_btn,
            fit_btn,
            actual_btn,
        ]

        bar.pack_end(actual_btn, False, False, 0)
        bar.pack_end(fit_btn, False, False, 0)
        bar.pack_end(self.zoom_in_btn, False, False, 0)
        bar.pack_end(self.zoom_label, False, False, 0)
        bar.pack_end(self.zoom_out_btn, False, False, 0)
        return bar

    def _zoom_button(self, label, tooltip, handler):
        btn = Gtk.Button(label=label)
        btn.set_relief(Gtk.ReliefStyle.NONE)
        btn.set_tooltip_text(tooltip)
        btn.connect("clicked", lambda *_: handler())
        return btn

    def icon_button(self, icon, tooltip, handler):
        btn = Gtk.Button()
        btn.set_relief(Gtk.ReliefStyle.NONE)
        btn.set_image(Gtk.Image.new_from_icon_name(icon, Gtk.IconSize.BUTTON))
        btn.set_tooltip_text(tooltip)
        btn.connect("clicked", lambda *_: handler())
        return btn

    def menu_button(self):
        menu = Gtk.Menu()

        self._menu_item(menu, "Open Image...", "gannotate-open-symbolic", self.open_file)
        menu.append(Gtk.SeparatorMenuItem())

        self.upload_menu_item = self._menu_item(
            menu, "Upload", "gannotate-upload-symbolic", self.upload
        )
        self.save_menu_item = self._menu_item(
            menu, "Save...", "gannotate-save-symbolic", self.save_dialog
        )
        menu.append(Gtk.SeparatorMenuItem())

        self._menu_item(
            menu, "Preferences...", "gannotate-preferences-symbolic", self.open_preferences
        )
        self._menu_item(menu, "About", "gannotate-about-symbolic", self.open_about)
        menu.append(Gtk.SeparatorMenuItem())

        self._menu_item(menu, "Close", "gannotate-close-symbolic", self.cancel)
        menu.show_all()

        btn = Gtk.MenuButton()
        btn.set_relief(Gtk.ReliefStyle.NONE)
        btn.set_image(
            Gtk.Image.new_from_icon_name(
                "gannotate-menu-symbolic", Gtk.IconSize.BUTTON
            )
        )
        btn.set_tooltip_text("Menu")
        btn.set_popup(menu)
        self.menu_btn = btn
        return btn

    def _menu_item(self, menu, label, icon, handler):
        item = Gtk.ImageMenuItem.new_with_mnemonic(label)
        item.set_image(Gtk.Image.new_from_icon_name(icon, Gtk.IconSize.MENU))
        item.set_always_show_image(True)
        item.connect("activate", lambda *_: handler())
        menu.append(item)
        return item

    # --- toolbar state ---
    def on_tool(self, btn, key):
        if btn.get_active():
            self.tool = key
            for other_key, other in self.tool_buttons.items():
                if other_key != key and other.get_active():
                    other.set_active(False)
            if key != "select":
                self.selected = None
        elif key == self.tool:
            btn.set_active(True)
        self.area.queue_draw()

    def on_color(self, btn):
        c = btn.get_rgba()
        self.color = (c.red, c.green, c.blue)

    def on_width(self, spin):
        self.width = int(spin.get_value())

    @staticmethod
    def _config_color(value):
        try:
            r, g, b = (float(v) for v in value[:3])
            return (
                min(max(r, 0.0), 1.0),
                min(max(g, 0.0), 1.0),
                min(max(b, 0.0), 1.0),
            )
        except Exception:
            return (0.95, 0.15, 0.15)

    @staticmethod
    def _config_width(value):
        try:
            return min(max(int(value), 1), 30)
        except Exception:
            return 4

    @staticmethod
    def _config_arrow_style(value):
        return value if value in ARROW_STYLES else "classic"

    def update_upload_state(self):
        has_image = self.base_surface is not None
        enabled = has_image and bool(self.upload_command.strip())
        if not has_image:
            tooltip = "Open an image first"
        elif enabled:
            tooltip = "Upload (Enter)"
        else:
            tooltip = "Set an upload command in Preferences"
        self.upload_btn.set_sensitive(enabled)
        self.upload_btn.set_tooltip_text(tooltip)
        if getattr(self, "upload_menu_item", None) is not None:
            self.upload_menu_item.set_sensitive(enabled)

    def set_image_controls(self, enabled):
        for btn in self.tool_buttons.values():
            btn.set_sensitive(enabled)
        self.color_btn.set_sensitive(enabled)
        self.width_spin.set_sensitive(enabled)
        self.undo_btn.set_sensitive(enabled)
        self.redo_btn.set_sensitive(enabled)
        self.save_btn.set_sensitive(enabled)
        for btn in getattr(self, "zoom_buttons", []):
            btn.set_sensitive(enabled)
        if getattr(self, "save_menu_item", None) is not None:
            self.save_menu_item.set_sensitive(enabled)
        self.update_upload_state()
        if not enabled:
            self.upload_btn.set_sensitive(False)
            self.upload_btn.set_tooltip_text("Open an image first")
            if getattr(self, "upload_menu_item", None) is not None:
                self.upload_menu_item.set_sensitive(False)

    # --- coordinate helpers ---
    def img_coords(self, x, y):
        return (x / self.scale, y / self.scale)

    def clamp(self, p):
        return (min(max(p[0], 0), self.img_w), min(max(p[1], 0), self.img_h))

    def screen_handles(self, a):
        x0, y0, x1, y1 = bbox(a)
        s = self.scale
        return [(x0 * s, y0 * s), (x1 * s, y0 * s), (x1 * s, y1 * s), (x0 * s, y1 * s)]

    # --- history ---
    def push_history(self):
        self.history.append(copy.deepcopy(self.annots))
        self.future.clear()

    def ensure_history(self):
        if self.pending_history:
            self.push_history()
            self.pending_history = False

    def undo(self):
        if not self.history:
            return
        self.future.append(copy.deepcopy(self.annots))
        self.annots = self.history.pop()
        self.selected = None
        self.area.queue_draw()

    def redo_last(self):
        if not self.future:
            return
        self.history.append(copy.deepcopy(self.annots))
        self.annots = self.future.pop()
        self.selected = None
        self.area.queue_draw()

    # --- mouse events ---
    def on_press(self, widget, ev):
        if self.base_surface is None:
            return False
        if ev.button == 2 or (
            ev.button == 1 and (ev.state & Gdk.ModifierType.CONTROL_MASK)
        ):
            self.pan_start = (
                ev.x_root,
                ev.y_root,
                self.hadj.get_value(),
                self.vadj.get_value(),
            )
            self._set_cursor("grabbing")
            return True
        if ev.button != 1:
            return False
        p = self.clamp(self.img_coords(ev.x, ev.y))
        if self.tool == "select":
            return self.select_press(ev, p)
        if self.tool == "text":
            text = self.prompt_text()
            if text:
                self.push_history()
                self.annots.append(self.make_text(p, text))
                self.area.queue_draw()
            return True
        self.current = {
            "type": self.tool,
            "p0": p,
            "p1": p,
            "points": [p],
            "color": self.color,
            "width": self.width,
        }
        self.area.queue_draw()
        return True

    def on_motion(self, widget, ev):
        if self.pan_start is not None:
            dx = ev.x_root - self.pan_start[0]
            dy = ev.y_root - self.pan_start[1]
            self.hadj.set_value(max(0.0, self.pan_start[2] - dx))
            self.vadj.set_value(max(0.0, self.pan_start[3] - dy))
            return True
        if self.drag_mode:
            p = self.clamp(self.img_coords(ev.x, ev.y))
            if self.drag_mode == "move":
                dx = p[0] - self.drag_start[0]
                dy = p[1] - self.drag_start[1]
                if abs(dx) < 0.05 and abs(dy) < 0.05:
                    return True
                self.ensure_history()
                self.annots[self.drag_index] = translate(self.drag_orig, dx, dy)
            else:
                ax, ay = self.drag_anchor
                cx, cy = self.drag_corner
                sx = (p[0] - ax) / (cx - ax) if abs(cx - ax) > 1e-6 else 1.0
                sy = (p[1] - ay) / (cy - ay) if abs(cy - ay) > 1e-6 else 1.0
                sx, sy = max(0.05, sx), max(0.05, sy)
                if abs(sx - 1) < 0.001 and abs(sy - 1) < 0.001:
                    return True
                self.ensure_history()
                self.annots[self.drag_index] = scale_annotation(
                    self.drag_orig, sx, sy, ax, ay, measure_text
                )
            self.area.queue_draw()
            return True
        if self.current is None:
            return False
        p = self.clamp(self.img_coords(ev.x, ev.y))
        self.current["p1"] = p
        if self.current["type"] in ("pen", "mark"):
            self.current["points"].append(p)
        self.area.queue_draw()
        return True

    def on_release(self, widget, ev):
        if self.pan_start is not None:
            self.pan_start = None
            self._set_cursor(None)
            return True
        if self.drag_mode:
            self.drag_mode = None
            self.drag_orig = None
            self.pending_history = False
            self.area.queue_draw()
            return True
        if self.current is None:
            return False
        if self.current["type"] in ("pen", "mark"):
            ok = len(self.current["points"]) > 1
        else:
            ok = math.dist(self.current["p0"], self.current["p1"]) > 2 / max(self.scale, 0.01)
        if ok:
            self.push_history()
            self.annots.append(self.current)
        self.current = None
        self.area.queue_draw()
        return True

    def select_press(self, ev, p):
        if self.selected is not None and 0 <= self.selected < len(self.annots):
            for idx, (hx, hy) in enumerate(self.screen_handles(self.annots[self.selected])):
                if abs(ev.x - hx) <= HANDLE and abs(ev.y - hy) <= HANDLE:
                    self.start_resize(idx)
                    return True
        for i in range(len(self.annots) - 1, -1, -1):
            if hit(self.annots[i], p, self.scale):
                self.selected = i
                self.drag_mode = "move"
                self.drag_index = i
                self.drag_start = p
                self.drag_orig = copy.deepcopy(self.annots[i])
                self.pending_history = True
                self.area.queue_draw()
                return True
        self.selected = None
        self.area.queue_draw()
        return True

    def start_resize(self, handle):
        self.selected = min(self.selected, len(self.annots) - 1)
        self.drag_mode = "resize"
        self.drag_index = self.selected
        self.drag_orig = copy.deepcopy(self.annots[self.selected])
        x0, y0, x1, y1 = bbox(self.drag_orig)
        corners = [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]
        self.drag_corner = corners[handle]
        self.drag_anchor = corners[(handle + 2) % 4]
        self.pending_history = True

    def on_key(self, widget, ev):
        key = ev.keyval
        ctrl = bool(ev.state & Gdk.ModifierType.CONTROL_MASK)
        shift = bool(ev.state & Gdk.ModifierType.SHIFT_MASK)
        if key == Gdk.KEY_Escape:
            self.cancel()
            return True
        if key in (Gdk.KEY_plus, Gdk.KEY_equal, Gdk.KEY_KP_Add):
            self.zoom_in()
            return True
        if key in (Gdk.KEY_minus, Gdk.KEY_KP_Subtract):
            self.zoom_out()
            return True
        if ctrl and key in (Gdk.KEY_0, Gdk.KEY_KP_0):
            self.zoom_fit()
            return True
        if ctrl and key in (Gdk.KEY_1, Gdk.KEY_KP_1):
            self.zoom_actual()
            return True
        if key in (Gdk.KEY_Return, Gdk.KEY_KP_Enter) and not ctrl:
            self.upload()
            return True
        if ctrl and key in (Gdk.KEY_s, Gdk.KEY_S):
            self.save_dialog()
            return True
        if ctrl and key in (Gdk.KEY_z, Gdk.KEY_Z):
            self.redo_last() if shift else self.undo()
            return True
        if ctrl and key in (Gdk.KEY_y, Gdk.KEY_Y):
            self.redo_last()
            return True
        if key in (Gdk.KEY_Delete, Gdk.KEY_BackSpace) and self.selected is not None:
            self.delete_selected()
            return True
        return False

    def delete_selected(self):
        if self.selected is None or not (0 <= self.selected < len(self.annots)):
            return
        self.push_history()
        del self.annots[self.selected]
        self.selected = None
        self.area.queue_draw()

    # --- text ---
    def make_text(self, p, text):
        size = max(14, self.width * 5)
        tw, th = measure_text(text, size)
        return {
            "type": "text",
            "p0": p,
            "text": text,
            "color": self.color,
            "size": size,
            "tw": tw,
            "th": th,
        }

    def prompt_text(self):
        dlg = Gtk.Dialog(title="Text")
        dlg.set_transient_for(self)
        dlg.set_modal(True)
        dlg.add_buttons(
            Gtk.STOCK_CANCEL,
            Gtk.ResponseType.CANCEL,
            Gtk.STOCK_OK,
            Gtk.ResponseType.OK,
        )
        entry = Gtk.Entry()
        entry.set_activates_default(True)
        dlg.get_content_area().add(entry)
        dlg.set_default_response(Gtk.ResponseType.OK)
        dlg.show_all()
        resp = dlg.run()
        text = entry.get_text()
        dlg.destroy()
        return text if resp == Gtk.ResponseType.OK and text.strip() else None

    # --- drawing ---
    def on_draw(self, widget, cr):
        if self.base_surface is None:
            color = self.get_style_context().get_background_color(Gtk.StateFlags.NORMAL)
            if color.alpha == 0:
                cr.set_source_rgb(0.12, 0.12, 0.12)
            else:
                cr.set_source_rgba(color.red, color.green, color.blue, color.alpha)
            cr.paint()
            return False
        cr.save()
        cr.scale(self.scale, self.scale)
        cr.set_source_surface(self.base_surface, 0, 0)
        cr.paint()
        for a in self.annots:
            draw_annotation(cr, a, self.arrow_style)
        if self.current is not None:
            draw_annotation(cr, self.current, self.arrow_style)
        cr.restore()
        self.draw_selection(cr)
        return False

    def draw_selection(self, cr):
        if self.selected is None or not (0 <= self.selected < len(self.annots)):
            return
        x0, y0, x1, y1 = bbox(self.annots[self.selected])
        s = self.scale
        X0, Y0, X1, Y1 = x0 * s, y0 * s, x1 * s, y1 * s
        cr.set_source_rgba(0.10, 0.55, 1.0, 0.95)
        cr.set_line_width(1.0)
        cr.set_dash([4, 4])
        cr.rectangle(X0, Y0, X1 - X0, Y1 - Y0)
        cr.stroke()
        cr.set_dash([])
        for hx, hy in ((X0, Y0), (X1, Y0), (X1, Y1), (X0, Y1)):
            cr.rectangle(hx - HANDLE / 2, hy - HANDLE / 2, HANDLE, HANDLE)
            cr.fill()

    # --- output ---
    def _set_image(self, pixbuf):
        self.pixbuf = pixbuf
        self.img_w = pixbuf.get_width()
        self.img_h = pixbuf.get_height()
        self.base_surface = Gdk.cairo_surface_create_from_pixbuf(pixbuf, 1, None)
        self.scale = 1.0
        return self.img_w, self.img_h

    def load_image(self, path):
        dw, dh = self._set_image(GdkPixbuf.Pixbuf.new_from_file(path))
        self.current_path = path
        self.annots = []
        self.history = []
        self.future = []
        self.current = None
        self.selected = None
        self.drag_mode = None
        self.result_path = None
        self.upload_after = False
        self.area.set_size_request(dw, dh)
        self.set_title(f"{__app_name__} - {os.path.basename(path)}")
        self.set_image_controls(True)
        target_w, target_h = self._default_window_size()
        self._fallback_viewport = (
            target_w,
            max(1, target_h - self._chrome_height()),
        )
        self.resize(target_w, target_h)
        self.zoom_fit_mode = True
        self.zoom_fit()
        GLib.idle_add(self._fit_after_show)
        self.update_info_label()
        self.area.queue_draw()

    def _workarea(self):
        display = Gdk.Display.get_default()
        monitor = display.get_primary_monitor() or display.get_monitor(0)
        try:
            area = monitor.get_workarea()
        except Exception:
            area = monitor.get_geometry()
        return area.width, area.height

    def _chrome_height(self):
        toolbar = self.toolbar.get_allocated_height()
        status = self.statusbar.get_allocated_height()
        if toolbar < 10:
            toolbar = 44
        if status < 10:
            status = 36
        return toolbar + status + 10

    def _default_window_size(self):
        max_w, max_h = self._workarea()
        max_w = int(max_w * 0.92)
        max_h = int(max_h * 0.88)
        chrome = self._chrome_height()
        width = max(640, min(self.img_w, max_w))
        height = max(420, min(self.img_h + chrome, max_h))
        return width, height

    def _view_size(self):
        vw = self.scrolled.get_allocated_width()
        vh = self.scrolled.get_allocated_height()
        if vw < 50 or vh < 50:
            return self._fallback_viewport
        return max(1, vw), max(1, vh)

    def _compute_fit_scale(self):
        vw, vh = self._view_size()
        return min(1.0, vw / max(1, self.img_w), vh / max(1, self.img_h))

    def _fit_after_show(self):
        if self.base_surface is not None and self.zoom_fit_mode:
            self.zoom_fit()
        return False

    def on_viewport_resize(self, widget, allocation):
        if self.base_surface is None or not self.zoom_fit_mode:
            return
        if self._fit_pending:
            return
        self._fit_pending = True
        GLib.idle_add(self._fit_idle)

    def _fit_idle(self):
        self._fit_pending = False
        if self.base_surface is not None and self.zoom_fit_mode:
            self._apply_zoom(self._compute_fit_scale(), keep_fit=True, reset=True)
        return False

    def _apply_zoom(self, scale, anchor=None, keep_fit=False, reset=False):
        if self.base_surface is None:
            return
        new_scale = min(max(scale, 0.05), 8.0)
        old = self.scale or 1.0
        vw, vh = self._view_size()
        if reset:
            anchor = (0.0, 0.0)
            h_off = v_off = 0.0
        else:
            if anchor is None:
                anchor = (vw / 2.0, vh / 2.0)
            h_off = self.hadj.get_value()
            v_off = self.vadj.get_value()
        ix = (h_off + anchor[0]) / old
        iy = (v_off + anchor[1]) / old
        self.scale = new_scale
        self.zoom_fit_mode = keep_fit
        self.area.set_size_request(
            max(1, int(round(self.img_w * new_scale))),
            max(1, int(round(self.img_h * new_scale))),
        )
        self.area.queue_resize()
        self.zoom_label.set_text(f"{new_scale * 100:.0f}%")
        self.area.queue_draw()
        if reset:
            target = (0.0, 0.0)
        else:
            target = (ix * new_scale - anchor[0], iy * new_scale - anchor[1])
        GLib.idle_add(self._set_scroll, target[0], target[1])

    def _set_scroll(self, h, v):
        self.hadj.set_value(max(0.0, h))
        self.vadj.set_value(max(0.0, v))
        return False

    def _set_cursor(self, name):
        try:
            window = self.area.get_window()
            if window is None:
                return
            cursor = None
            if name:
                cursor = Gdk.Cursor.new_from_name(
                    Gdk.Display.get_default(), name
                )
            window.set_cursor(cursor)
        except Exception:
            pass

    def zoom_in(self):
        if self.base_surface is not None:
            self._apply_zoom(self.scale * 1.25)

    def zoom_out(self):
        if self.base_surface is not None:
            self._apply_zoom(self.scale / 1.25)

    def zoom_fit(self):
        if self.base_surface is not None:
            self.zoom_fit_mode = True
            self._apply_zoom(self._compute_fit_scale(), keep_fit=True, reset=True)

    def zoom_actual(self):
        if self.base_surface is not None:
            self._apply_zoom(1.0)

    def on_scroll(self, widget, ev):
        if self.base_surface is None or not (
            ev.state & Gdk.ModifierType.CONTROL_MASK
        ):
            return False
        if ev.direction == Gdk.ScrollDirection.SMOOTH:
            ok, _dx, dy = ev.get_scroll_deltas()
            if not ok:
                return False
            factor = 1.1 ** (-dy)
        elif ev.direction == Gdk.ScrollDirection.UP:
            factor = 1.25
        elif ev.direction == Gdk.ScrollDirection.DOWN:
            factor = 0.8
        else:
            return False
        h_off = self.hadj.get_value()
        v_off = self.vadj.get_value()
        self._apply_zoom(
            self.scale * factor, anchor=(ev.x - h_off, ev.y - v_off)
        )
        return True

    def update_info_label(self):
        if self.base_surface is None:
            self.info_label.set_text("No image")
            self.zoom_label.set_text("\u2014")
        else:
            self.info_label.set_text(f"{self.img_w} \u00d7 {self.img_h}")

    def _start_dir(self):
        if self.current_path:
            return os.path.dirname(self.current_path)
        return os.path.expanduser("~/Pictures")

    def open_file(self):
        dlg = Gtk.FileChooserDialog(title="Open image", action=Gtk.FileChooserAction.OPEN)
        dlg.set_transient_for(self)
        dlg.add_buttons(
            Gtk.STOCK_CANCEL,
            Gtk.ResponseType.CANCEL,
            Gtk.STOCK_OPEN,
            Gtk.ResponseType.OK,
        )
        images = Gtk.FileFilter()
        images.set_name("Images")
        for pattern in ("*.png", "*.jpg", "*.jpeg", "*.webp", "*.bmp", "*.gif", "*.tif", "*.tiff"):
            images.add_pattern(pattern)
        dlg.add_filter(images)
        all_files = Gtk.FileFilter()
        all_files.set_name("All files")
        all_files.add_pattern("*")
        dlg.add_filter(all_files)
        current_dir = self._start_dir()
        if current_dir and os.path.isdir(current_dir):
            dlg.set_current_folder(current_dir)
        resp = dlg.run()
        path = dlg.get_filename()
        dlg.destroy()
        if resp == Gtk.ResponseType.OK and path:
            try:
                self.load_image(path)
            except Exception as exc:
                self.show_error(f"Could not open image:\n{exc}")

    def show_error(self, message):
        dlg = Gtk.MessageDialog(
            flags=0,
            message_type=Gtk.MessageType.ERROR,
            buttons=Gtk.ButtonsType.CLOSE,
            text=message,
        )
        dlg.set_transient_for(self)
        dlg.run()
        dlg.destroy()

    def cancel(self):
        self.result_path = None
        self.upload_after = False
        self.close()

    def upload(self):
        if self.base_surface is None:
            return
        if not self.upload_command.strip():
            return
        folder = tempfile.mkdtemp(prefix="gannotate-")
        path = os.path.join(folder, "annotated.png")
        flatten(
            self.base_surface,
            self.annots,
            self.img_w,
            self.img_h,
            path,
            self.arrow_style,
        )
        self.result_path = path
        self.upload_after = True
        self.close()

    def save_dialog(self):
        if self.base_surface is None:
            return
        dlg = Gtk.FileChooserDialog(
            title="Save screenshot",
            action=Gtk.FileChooserAction.SAVE,
        )
        dlg.set_transient_for(self)
        dlg.add_buttons(
            Gtk.STOCK_CANCEL,
            Gtk.ResponseType.CANCEL,
            Gtk.STOCK_SAVE,
            Gtk.ResponseType.OK,
        )
        dlg.set_do_overwrite_confirmation(True)
        dlg.set_default_response(Gtk.ResponseType.OK)
        dlg.set_current_name(time.strftime("screenshot-%Y%m%d-%H%M%S.png"))
        folder = os.path.expanduser("~/Pictures/Screenshots")
        if os.path.isdir(folder):
            dlg.set_current_folder(folder)
        resp = dlg.run()
        path = dlg.get_filename()
        dlg.destroy()
        if resp == Gtk.ResponseType.OK and path:
            flatten(
                self.base_surface,
                self.annots,
                self.img_w,
                self.img_h,
                path,
                self.arrow_style,
            )
            self.result_path = path
            self.upload_after = False
            self.close()

    # --- dialogs ---
    def open_preferences(self):
        dlg = Gtk.Dialog(title=f"{__app_name__} Preferences")
        dlg.set_transient_for(self)
        dlg.set_modal(True)
        dlg.set_default_size(430, 300)

        notebook = Gtk.Notebook()
        notebook.set_border_width(8)
        dlg.get_content_area().pack_start(notebook, True, True, 0)

        # General tab
        general = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        general.set_border_width(12)
        grid = Gtk.Grid(column_spacing=12, row_spacing=10)

        color_label = Gtk.Label(label="Default color")
        color_label.set_xalign(0)
        grid.attach(color_label, 0, 0, 1, 1)

        color_btn = Gtk.ColorButton()
        rgba = Gdk.RGBA()
        rgba.red, rgba.green, rgba.blue, rgba.alpha = *self.color, 1.0
        color_btn.set_rgba(rgba)
        grid.attach(color_btn, 1, 0, 1, 1)

        width_label = Gtk.Label(label="Default line width")
        width_label.set_xalign(0)
        grid.attach(width_label, 0, 1, 1, 1)

        width_spin = Gtk.SpinButton.new_with_range(1, 30, 1)
        width_spin.set_value(self.width)
        grid.attach(width_spin, 1, 1, 1, 1)

        style_label = Gtk.Label(label="Arrow head")
        style_label.set_xalign(0)
        grid.attach(style_label, 0, 2, 1, 1)

        fg = dlg.get_style_context().get_color(Gtk.StateFlags.NORMAL)
        store = Gtk.ListStore(GdkPixbuf.Pixbuf, str, str)
        for key, label in ARROW_STYLE_LABELS:
            store.append([_arrow_pixbuf(key, fg), label, key])

        style_combo = Gtk.ComboBox(model=store)
        icon_cell = Gtk.CellRendererPixbuf()
        style_combo.pack_start(icon_cell, False)
        style_combo.add_attribute(icon_cell, "pixbuf", 0)
        text_cell = Gtk.CellRendererText()
        style_combo.pack_start(text_cell, True)
        style_combo.add_attribute(text_cell, "text", 1)
        for index, row in enumerate(store):
            if row[2] == self.arrow_style:
                style_combo.set_active(index)
                break
        grid.attach(style_combo, 1, 2, 1, 1)

        general.pack_start(grid, False, False, 0)

        notebook.append_page(general, Gtk.Label(label="General"))

        # Upload tab
        upload = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        upload.set_border_width(12)

        upload_label = Gtk.Label(label="Upload command (optional)")
        upload_label.set_xalign(0)
        upload.pack_start(upload_label, False, False, 0)

        entry = Gtk.Entry()
        entry.set_text(self.upload_command)
        entry.set_hexpand(True)
        upload.pack_start(entry, False, False, 0)

        hint = Gtk.Label()
        hint.set_markup(
            "<small>Use <tt>%f</tt> for the file path. "
            "Leave empty to disable uploads.</small>"
        )
        hint.set_xalign(0)
        hint.set_line_wrap(True)
        upload.pack_start(hint, False, False, 0)

        row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        browse = Gtk.Button(label="Browse...")
        browse.connect("clicked", lambda *_: self.browse_command(entry))
        row.pack_start(browse, False, False, 0)
        reset = Gtk.Button(label="Reset")
        reset.connect("clicked", lambda *_: entry.set_text(""))
        row.pack_start(reset, False, False, 0)
        upload.pack_start(row, False, False, 0)

        notebook.append_page(upload, Gtk.Label(label="Upload"))

        # Close button (only action)
        close_btn = Gtk.Button()
        close_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        close_box.pack_start(
            Gtk.Image.new_from_icon_name(
                "gannotate-close-symbolic", Gtk.IconSize.BUTTON
            ),
            False,
            False,
            0,
        )
        close_box.pack_start(Gtk.Label(label="Close"), False, False, 0)
        close_btn.add(close_box)
        close_btn.connect("clicked", lambda *_: dlg.response(Gtk.ResponseType.CLOSE))
        dlg.add_action_widget(close_btn, Gtk.ResponseType.CLOSE)

        dlg.show_all()
        dlg.run()

        self.upload_command = entry.get_text().strip()
        self.config["upload_command"] = self.upload_command

        rgba = color_btn.get_rgba()
        self.color = self._config_color([rgba.red, rgba.green, rgba.blue])
        self.config["default_color"] = list(self.color)
        self.color_btn.set_rgba(rgba)

        self.width = self._config_width(width_spin.get_value())
        self.config["default_width"] = self.width
        self.width_spin.set_value(self.width)

        active = style_combo.get_active_iter()
        style_key = store[active][2] if active is not None else self.arrow_style
        self.arrow_style = self._config_arrow_style(style_key)
        self.config["arrow_style"] = self.arrow_style
        self.area.queue_draw()

        save_config(self.config)
        self.update_upload_state()
        dlg.destroy()

    def browse_command(self, entry):
        dlg = Gtk.FileChooserDialog(
            title="Select upload command",
            action=Gtk.FileChooserAction.OPEN,
        )
        dlg.set_transient_for(self)
        dlg.add_buttons(
            Gtk.STOCK_CANCEL,
            Gtk.ResponseType.CANCEL,
            Gtk.STOCK_OPEN,
            Gtk.ResponseType.OK,
        )
        resp = dlg.run()
        path = dlg.get_filename()
        dlg.destroy()
        if resp == Gtk.ResponseType.OK and path:
            entry.set_text(f"{path} %f")

    def open_about(self):
        dlg = Gtk.AboutDialog()
        dlg.set_transient_for(self)
        dlg.set_modal(True)
        dlg.set_program_name(__app_name__)
        dlg.set_version(__version__)
        dlg.set_comments("A lightweight screenshot annotator built with GTK3 and Cairo.")
        dlg.set_copyright("Copyright (c) 2026 arodu")
        dlg.set_authors(["arodu https://github.com/arodu"])
        dlg.set_website("https://github.com/arodu/gannotate")
        if hasattr(Gtk.License, "GPL_3_0"):
            dlg.set_license_type(Gtk.License.GPL_3_0)
        try:
            dlg.set_logo(GdkPixbuf.Pixbuf.new_from_file(ICON_PATH))
        except Exception:
            pass
        dlg.run()
        dlg.destroy()
