import unittest

from gannotate import model


def rect():
    return {"type": "rect", "p0": (10, 20), "p1": (110, 80), "color": (1, 0, 0), "width": 4}


def arrow():
    return {"type": "arrow", "p0": (0, 0), "p1": (100, 0), "color": (1, 0, 0), "width": 4}


def pen():
    return {
        "type": "pen",
        "p0": (0, 0),
        "p1": (10, 0),
        "points": [(0, 0), (5, 5), (10, 0)],
        "color": (0, 0, 1),
        "width": 2,
    }


def text():
    return {
        "type": "text",
        "p0": (10, 10),
        "text": "hi",
        "color": (0, 0, 0),
        "size": 20,
        "tw": 50,
        "th": 20,
    }


class BBoxTests(unittest.TestCase):
    def test_rect(self):
        self.assertEqual(model.bbox(rect()), (8, 18, 112, 82))

    def test_text(self):
        self.assertEqual(model.bbox(text()), (8, 8, 62, 32))

    def test_pen(self):
        self.assertEqual(model.bbox(pen()), (-1, -1, 11, 6))


class HitTests(unittest.TestCase):
    def test_rect_inside_and_outside(self):
        self.assertTrue(model.hit(rect(), (50, 50), 1.0))
        self.assertFalse(model.hit(rect(), (0, 0), 1.0))

    def test_arrow_near_and_far(self):
        self.assertTrue(model.hit(arrow(), (50, 3), 1.0))
        self.assertFalse(model.hit(arrow(), (50, 30), 1.0))

    def test_pen_near_and_far(self):
        self.assertTrue(model.hit(pen(), (5, 4), 1.0))
        self.assertFalse(model.hit(pen(), (5, 40), 1.0))


class TransformTests(unittest.TestCase):
    def test_translate(self):
        moved = model.translate(rect(), 5, -5)
        self.assertEqual(moved["p0"], (15, 15))
        self.assertEqual(moved["p1"], (115, 75))

    def test_translate_does_not_mutate_original(self):
        original = rect()
        model.translate(original, 100, 100)
        self.assertEqual(original["p0"], (10, 20))

    def test_scale(self):
        scaled = model.scale_annotation(rect(), 2.0, 2.0, 10, 20, lambda t, s: (1, 1))
        self.assertEqual(scaled["p0"], (10, 20))
        self.assertEqual(scaled["p1"], (210, 140))

    def test_scale_text_updates_size(self):
        def measure(value, size):
            return (len(value) * int(size), int(size))

        scaled = model.scale_annotation(text(), 2.0, 2.0, 0, 0, measure)
        self.assertEqual(scaled["size"], 40)
        self.assertEqual(scaled["tw"], 80)


if __name__ == "__main__":
    unittest.main()
