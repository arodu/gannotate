import os
import tempfile
import unittest
from unittest import mock

try:
    import gi

    gi.require_version("Gtk", "3.0")
    from gi.repository import Gtk
    import cairo

    from gannotate.app import Gannotate

    HAVE_UI = True
except Exception:
    HAVE_UI = False


def make_png(path, width=120, height=80):
    surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, width, height)
    cr = cairo.Context(surface)
    cr.set_source_rgb(1, 0, 0)
    cr.paint()
    surface.write_to_png(path)


@unittest.skipUnless(HAVE_UI and os.environ.get("DISPLAY"), "needs GTK and a display")
class AppTests(unittest.TestCase):
    def setUp(self):
        self.app = Gannotate(
            None,
            {
                "upload_command": "true %f",
                "default_color": [0.9, 0.1, 0.1],
                "default_width": 4,
            },
        )

    def tearDown(self):
        self.app.destroy()
        while Gtk.events_pending():
            Gtk.main_iteration()

    def open_item(self):
        menu = self.app.menu_btn.get_popup()
        for child in menu.get_children():
            if isinstance(child, Gtk.ImageMenuItem) and child.get_label() == "Open Image...":
                return child
        return None

    def test_blank_state(self):
        self.assertIsNone(self.app.base_surface)
        self.assertIsNone(self.app.current_path)
        self.assertEqual(self.app.get_title(), "Gannotate")
        self.assertEqual(self.app.arrow_style, "classic")
        self.assertEqual(self.app._config_arrow_style("slim"), "slim")
        self.assertEqual(self.app._config_arrow_style("bogus"), "classic")

        for button in self.app.tool_buttons.values():
            self.assertFalse(button.get_sensitive())

        for widget in (
            self.app.color_btn,
            self.app.width_spin,
            self.app.undo_btn,
            self.app.redo_btn,
            self.app.save_btn,
            self.app.upload_btn,
            self.app.save_menu_item,
            self.app.upload_menu_item,
        ):
            self.assertFalse(widget.get_sensitive())

        open_item = self.open_item()
        self.assertIsNotNone(open_item)
        self.assertTrue(open_item.get_sensitive())

    def test_start_dir_blank(self):
        self.assertEqual(self.app._start_dir(), os.path.expanduser("~/Pictures"))

    def test_load_image_enables_controls(self):
        with tempfile.TemporaryDirectory() as folder:
            path = os.path.join(folder, "test.png")
            make_png(path)
            self.app.load_image(path)

            self.assertIsNotNone(self.app.base_surface)
            self.assertEqual(self.app.img_w, 120)
            self.assertEqual(self.app.img_h, 80)
            self.assertIn("test.png", self.app.get_title())
            self.assertEqual(self.app._start_dir(), folder)

            self.assertTrue(self.app.tool_buttons["arrow"].get_sensitive())
            self.assertTrue(self.app.color_btn.get_sensitive())
            self.assertTrue(self.app.width_spin.get_sensitive())
            self.assertTrue(self.app.undo_btn.get_sensitive())
            self.assertTrue(self.app.redo_btn.get_sensitive())
            self.assertTrue(self.app.save_btn.get_sensitive())
            self.assertTrue(self.app.upload_btn.get_sensitive())
            self.assertTrue(self.app.save_menu_item.get_sensitive())
            self.assertTrue(self.app.upload_menu_item.get_sensitive())

            self.app.set_image_controls(False)
            self.assertFalse(self.app.tool_buttons["arrow"].get_sensitive())
            self.assertFalse(self.app.save_btn.get_sensitive())
            self.assertFalse(self.app.upload_btn.get_sensitive())

    def test_upload_disabled_without_command(self):
        with tempfile.TemporaryDirectory() as folder:
            path = os.path.join(folder, "test.png")
            make_png(path)
            self.app.upload_command = ""
            self.app.load_image(path)

            self.assertTrue(self.app.save_btn.get_sensitive())
            self.assertFalse(self.app.upload_btn.get_sensitive())
            self.assertFalse(self.app.upload_menu_item.get_sensitive())

    def test_open_file_from_blank(self):
        class FakeFileChooser:
            filename = None

            def __init__(self, *args, **kwargs):
                self.current_folder = None

            def set_transient_for(self, parent):
                pass

            def add_buttons(self, *args):
                pass

            def add_filter(self, filter_):
                pass

            def set_current_folder(self, folder):
                self.current_folder = folder

            def run(self):
                return Gtk.ResponseType.OK

            def get_filename(self):
                return self.filename

            def destroy(self):
                pass

        with tempfile.TemporaryDirectory() as folder:
            path = os.path.join(folder, "opened.png")
            make_png(path)
            FakeFileChooser.filename = path
            with mock.patch("gannotate.app.Gtk.FileChooserDialog", FakeFileChooser):
                self.app.open_file()

            self.assertEqual(self.app.current_path, path)
            self.assertIsNotNone(self.app.base_surface)
            self.assertIn("opened.png", self.app.get_title())


if __name__ == "__main__":
    unittest.main()
