"""Cairo rendering for Gannotate annotations."""

import math

import cairo

try:
    import gi

    gi.require_version("Pango", "1.0")
    gi.require_version("PangoCairo", "1.0")
    from gi.repository import Pango, PangoCairo

    HAVE_PANGO = True
except Exception:
    HAVE_PANGO = False


def font_desc(size):
    fd = Pango.FontDescription("Sans")
    fd.set_absolute_size(size * Pango.SCALE)
    return fd


def measure_text(text, size):
    if HAVE_PANGO:
        surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, 1, 1)
        cr = cairo.Context(surface)
        layout = PangoCairo.create_layout(cr)
        layout.set_text(text, -1)
        layout.set_font_description(font_desc(size))
        w, h = layout.get_pixel_size()
        return (max(1, w), max(1, h))
    return (max(1, int(len(text) * size * 0.6)), max(1, int(size * 1.3)))


def set_pen(cr, a):
    r, g, b = a["color"]
    cr.set_source_rgba(r, g, b, 0.35 if a["type"] == "mark" else 1.0)
    cr.set_line_width(a["width"])
    cr.set_line_cap(cairo.LINE_CAP_ROUND)
    cr.set_line_join(cairo.LINE_JOIN_ROUND)


def draw_text(cr, a):
    x, y = a["p0"]
    r, g, b = a["color"]
    cr.set_source_rgba(r, g, b, 1.0)
    if HAVE_PANGO:
        layout = PangoCairo.create_layout(cr)
        layout.set_text(a["text"], -1)
        layout.set_font_description(font_desc(a["size"]))
        cr.move_to(x, y)
        PangoCairo.show_layout(cr, layout)
    else:
        cr.select_font_face("Sans")
        cr.set_font_size(a["size"])
        cr.move_to(x, y)
        cr.show_text(a["text"])


def draw_arrow(cr, a):
    set_pen(cr, a)
    p0, p1 = a["p0"], a["p1"]
    dx, dy = p1[0] - p0[0], p1[1] - p0[1]
    length = math.hypot(dx, dy)
    if length < 1e-6:
        return

    ux, uy = dx / length, dy / length
    px, py = -uy, ux
    thickness = a["width"]

    # Proportions borrowed from the Font Awesome solid arrow:
    # head length ~3.6x thickness, width ~1.6x head length, notch at ~48%.
    head_len = min(max(thickness * 3.6, 12.0), length * 0.5)
    head_w = head_len * 1.6
    notch_depth = head_len * 0.48

    base_x, base_y = p1[0] - ux * head_len, p1[1] - uy * head_len
    notch_x, notch_y = base_x + ux * notch_depth, base_y + uy * notch_depth

    # Shaft ends at the notch plane, like the icon.
    cr.move_to(*p0)
    cr.line_to(notch_x, notch_y)
    cr.stroke()

    half = thickness / 2.0
    left = (base_x + px * head_w / 2, base_y + py * head_w / 2)
    right = (base_x - px * head_w / 2, base_y - py * head_w / 2)
    notch_left = (notch_x + px * half, notch_y + py * half)
    notch_right = (notch_x - px * half, notch_y - py * half)

    cr.move_to(*p1)
    cr.line_to(*left)
    cr.line_to(*notch_left)
    cr.line_to(*notch_right)
    cr.line_to(*right)
    cr.close_path()
    cr.fill()


def draw_annotation(cr, a):
    kind = a["type"]
    if kind in ("pen", "mark"):
        pts = a["points"]
        if len(pts) < 2:
            return
        set_pen(cr, a)
        cr.move_to(*pts[0])
        for p in pts[1:]:
            cr.line_to(*p)
        cr.stroke()
    elif kind == "line":
        set_pen(cr, a)
        cr.move_to(*a["p0"])
        cr.line_to(*a["p1"])
        cr.stroke()
    elif kind == "arrow":
        draw_arrow(cr, a)
    elif kind == "rect":
        x0, y0 = a["p0"]
        x1, y1 = a["p1"]
        set_pen(cr, a)
        cr.rectangle(min(x0, x1), min(y0, y1), abs(x1 - x0), abs(y1 - y0))
        cr.stroke()
    elif kind == "ellipse":
        x0, y0 = a["p0"]
        x1, y1 = a["p1"]
        cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
        rx, ry = abs(x1 - x0) / 2, abs(y1 - y0) / 2
        if rx > 0 and ry > 0:
            set_pen(cr, a)
            cr.save()
            cr.translate(cx, cy)
            cr.scale(rx, ry)
            cr.arc(0, 0, 1, 0, 2 * math.pi)
            cr.restore()
            cr.stroke()
    elif kind == "text":
        draw_text(cr, a)


def flatten(base_surface, annots, width, height, path):
    surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, width, height)
    cr = cairo.Context(surface)
    cr.set_source_surface(base_surface, 0, 0)
    cr.paint()
    for a in annots:
        draw_annotation(cr, a)
    surface.write_to_png(path)
