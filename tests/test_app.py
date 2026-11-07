import os
import tempfile
import unittest
from types import SimpleNamespace
from unittest import mock

try:
    import gi

    gi.require_version("Gtk", "3.0")
    gi.require_version("Gdk", "3.0")
    from gi.repository import Gdk, Gtk
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
        self.assertTrue(self.app.close_after_upload)
        self.assertFalse(self.app.uploading)

        for button in self.app.tool_buttons.values():
            self.assertFalse(button.get_sensitive())

        for widget in (
            self.app.color_btn,
            self.app.width_spin,
            self.app.undo_btn,
            self.app.redo_btn,
            self.app.save_btn,
            self.app.upload_btn,
            self.app.copy_btn,
            self.app.save_menu_item,
            self.app.upload_menu_item,
            self.app.copy_menu_item,
            *self.app.zoom_buttons,
        ):
            self.assertFalse(widget.get_sensitive())

        open_item = self.open_item()
        self.assertIsNotNone(open_item)
        self.assertTrue(open_item.get_sensitive())

    def test_toolbar_action_order(self):
        while Gtk.events_pending():
            Gtk.main_iteration()
        buttons = [self.app.upload_btn, self.app.copy_btn, self.app.save_btn]
        buttons.sort(key=lambda button: button.get_allocation().x)
        self.assertEqual(
            buttons, [self.app.upload_btn, self.app.copy_btn, self.app.save_btn]
        )

    def test_menu_action_order(self):
        menu = self.app.menu_btn.get_popup()
        labels = [
            child.get_label()
            for child in menu.get_children()
            if isinstance(child, Gtk.ImageMenuItem)
        ]
        start = labels.index("Save...")
        self.assertEqual(
            labels[start : start + 3],
            ["Save...", "Copy to Clipboard", "Upload"],
        )

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
            self.assertTrue(self.app.copy_btn.get_sensitive())
            self.assertTrue(self.app.save_menu_item.get_sensitive())
            self.assertTrue(self.app.upload_menu_item.get_sensitive())
            self.assertTrue(self.app.copy_menu_item.get_sensitive())
            for widget in self.app.zoom_buttons:
                self.assertTrue(widget.get_sensitive())

            self.app.zoom_actual()
            self.assertEqual(self.app.scale, 1.0)
            self.app.zoom_in()
            self.assertGreater(self.app.scale, 1.0)
            self.app.zoom_out()
            self.assertAlmostEqual(self.app.scale, 1.0)
            self.app.zoom_fit()
            self.assertGreater(self.app.scale, 0)
            self.assertLessEqual(self.app.scale, 1.0)

            self.app.set_image_controls(False)
            self.assertFalse(self.app.tool_buttons["arrow"].get_sensitive())
            self.assertFalse(self.app.save_btn.get_sensitive())
            self.assertFalse(self.app.upload_btn.get_sensitive())
            self.assertFalse(self.app.copy_btn.get_sensitive())
            self.assertFalse(self.app.copy_menu_item.get_sensitive())
            for widget in self.app.zoom_buttons:
                self.assertFalse(widget.get_sensitive())

    def test_zoom_fit_and_actual(self):
        with tempfile.TemporaryDirectory() as folder:
            path = os.path.join(folder, "test.png")
            make_png(path)
            self.app.load_image(path)
            self.assertTrue(self.app.get_resizable())

            with mock.patch.object(self.app, "_view_size", return_value=(60, 40)):
                self.app.zoom_fit()
            self.assertAlmostEqual(self.app.scale, 0.5, places=2)

            self.app.zoom_actual()
            self.assertEqual(self.app.scale, 1.0)
            self.app.zoom_in()
            self.assertGreater(self.app.scale, 1.0)

    def test_ctrl_drag_pans(self):
        with tempfile.TemporaryDirectory() as folder:
            path = os.path.join(folder, "test.png")
            make_png(path)
            self.app.load_image(path)

            press = SimpleNamespace(
                button=1,
                state=Gdk.ModifierType.CONTROL_MASK,
                x=10,
                y=10,
                x_root=100,
                y_root=100,
            )
            self.assertTrue(self.app.on_press(self.app.area, press))
            self.assertIsNotNone(self.app.pan_start)

            motion = SimpleNamespace(x_root=60, y_root=60)
            self.assertTrue(self.app.on_motion(self.app.area, motion))

            release = SimpleNamespace(button=1)
            self.assertTrue(self.app.on_release(self.app.area, release))
            self.assertIsNone(self.app.pan_start)

    def test_upload_disabled_without_command(self):
        with tempfile.TemporaryDirectory() as folder:
            path = os.path.join(folder, "test.png")
            make_png(path)
            self.app.upload_command = ""
            self.app.load_image(path)

            self.assertTrue(self.app.save_btn.get_sensitive())
            self.assertFalse(self.app.upload_btn.get_sensitive())
            self.assertFalse(self.app.upload_menu_item.get_sensitive())

    def test_copy_to_clipboard_keeps_window(self):
        with tempfile.TemporaryDirectory() as folder:
            path = os.path.join(folder, "test.png")
            make_png(path)
            self.app.load_image(path)

            clipboard = mock.Mock()
            with mock.patch.object(Gtk.Clipboard, "get", return_value=clipboard), mock.patch(
                "gannotate.app.notify"
            ) as notify:
                handled = self.app.on_key(
                    self.app,
                    SimpleNamespace(
                        keyval=Gdk.KEY_c,
                        state=Gdk.ModifierType.CONTROL_MASK,
                    ),
                )

            self.assertTrue(handled)
            notify.assert_called_once_with("Image copied to clipboard")
            clipboard.set_image.assert_called_once()
            clipboard.store.assert_called_once()
            pixbuf = clipboard.set_image.call_args[0][0]
            self.assertEqual((pixbuf.get_width(), pixbuf.get_height()), (120, 80))
            self.assertIsNone(self.app.result_path)
            self.assertFalse(self.app.upload_after)
            self.assertIsNotNone(self.app.base_surface)

    def test_upload_closes_window_by_default(self):
        with tempfile.TemporaryDirectory() as folder:
            path = os.path.join(folder, "test.png")
            make_png(path)
            self.app.load_image(path)
            self.app.upload_command = "true %f"

            with mock.patch(
                "gannotate.app.tempfile.mkdtemp", return_value=folder
            ), mock.patch("gannotate.app.flatten"), mock.patch.object(
                self.app, "close"
            ) as close:
                self.app.upload()

            close.assert_called_once()
            self.assertTrue(self.app.upload_after)
            self.assertEqual(self.app.result_path, os.path.join(folder, "annotated.png"))

    def test_upload_can_keep_window_open(self):
        with tempfile.TemporaryDirectory() as folder:
            path = os.path.join(folder, "test.png")
            make_png(path)
            self.app.load_image(path)
            self.app.upload_command = "true %f"
            self.app.close_after_upload = False

            with mock.patch(
                "gannotate.app.tempfile.mkdtemp", return_value=folder
            ), mock.patch("gannotate.app.flatten"), mock.patch(
                "gannotate.app.threading.Thread"
            ) as thread, mock.patch.object(self.app, "close") as close:
                self.app.upload()

            close.assert_not_called()
            thread.assert_called_once()
            thread.return_value.start.assert_called_once()
            self.assertFalse(self.app.upload_after)
            self.assertIsNone(self.app.result_path)
            self.assertTrue(self.app.uploading)

    def test_upload_failure_saves_local(self):
        with mock.patch("gannotate.app.run_upload", return_value=1), mock.patch(
            "gannotate.app.save_local", return_value="/tmp/saved.png"
        ) as save_local, mock.patch("gannotate.app.shutil.rmtree") as rmtree, mock.patch(
            "gannotate.app.notify"
        ) as notify, mock.patch(
            "gannotate.app.GLib.idle_add"
        ) as idle_add:
            self.app._upload_async("false %f", "/tmp/annotated.png", "/tmp/folder")

        save_local.assert_called_once_with("/tmp/annotated.png")
        rmtree.assert_called_once_with("/tmp/folder", ignore_errors=True)
        notify.assert_called_once_with(
            "Upload failed; screenshot saved: /tmp/saved.png"
        )
        idle_add.assert_called_once()

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
