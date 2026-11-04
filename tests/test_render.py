import unittest

import cairo

from gannotate import render

ARROW = {
    "type": "arrow",
    "p0": (10.0, 70.0),
    "p1": (190.0, 10.0),
    "color": (1.0, 1.0, 1.0),
    "width": 5,
}


def render_arrow(style):
    surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, 200, 80)
    cr = cairo.Context(surface)
    cr.set_source_rgb(0, 0, 0)
    cr.paint()
    render.draw_annotation(cr, ARROW, style)
    surface.flush()
    return bytes(surface.get_data())


class RenderTests(unittest.TestCase):
    def test_every_style_renders_differently(self):
        outputs = {style: render_arrow(style) for style in render.ARROW_STYLES}
        self.assertEqual(len(set(outputs.values())), len(render.ARROW_STYLES))

    def test_unknown_style_falls_back_to_classic(self):
        self.assertEqual(render_arrow("nope"), render_arrow("classic"))

    def test_flatten_uses_arrow_style(self):
        import os
        import tempfile

        base = cairo.ImageSurface(cairo.FORMAT_ARGB32, 200, 80)
        cr = cairo.Context(base)
        cr.set_source_rgb(0, 0, 0)
        cr.paint()
        outputs = []
        with tempfile.TemporaryDirectory() as folder:
            for style in render.ARROW_STYLES:
                path = os.path.join(folder, f"{style}.png")
                render.flatten(base, [ARROW], 200, 80, path, style)
                with open(path, "rb") as fh:
                    outputs.append(fh.read())
        self.assertEqual(len(set(outputs)), len(render.ARROW_STYLES))


if __name__ == "__main__":
    unittest.main()
