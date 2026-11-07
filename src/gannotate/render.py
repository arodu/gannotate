"""Cairo rendering for Gannotate annotations."""

import math

import cairo

ARROW_STYLES = ("classic", "triangle", "slim", "wide")

# Head-only variants: the shaft is always the same straight line.
# (length factor, width factor, notch factor, minimum head length)
_ARROW_SHAPES = {
    "classic": (3.6, 1.55, 0.48, 12.0),
    "triangle": (3.4, 1.45, 0.0, 12.0),
    "slim": (4.6, 1.10, 0.40, 14.0),
    "wide": (3.0, 1.90, 0.50, 11.0),
}

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


def _fill_head(cr, tip, ux, uy, head_len, head_w, notch, thickness):
    px, py = -uy, ux
    base_x, base_y = tip[0] - ux * head_len, tip[1] - uy * head_len
    notch_x, notch_y = base_x + ux * notch, base_y + uy * notch
    half = thickness / 2.0

    cr.move_to(*tip)
    cr.line_to(base_x + px * head_w / 2, base_y + py * head_w / 2)
    cr.line_to(notch_x + px * half, notch_y + py * half)
    cr.line_to(notch_x - px * half, notch_y - py * half)
    cr.line_to(base_x - px * head_w / 2, base_y - py * head_w / 2)
    cr.close_path()
    cr.fill()
    return notch_x, notch_y


def draw_arrow(cr, a, style="classic"):
    set_pen(cr, a)
    p0, p1 = a["p0"], a["p1"]
    dx, dy = p1[0] - p0[0], p1[1] - p0[1]
    length = math.hypot(dx, dy)
    if length < 1e-6:
        return

    ux, uy = dx / length, dy / length
    thickness = a["width"]

    len_f, wid_f, notch_f, min_len = _ARROW_SHAPES.get(
        style, _ARROW_SHAPES["classic"]
    )
    head_len = min(max(thickness * len_f, min_len), length * 0.55)
    head_w = head_len * wid_f
    notch_x, notch_y = _fill_head(
        cr, p1, ux, uy, head_len, head_w, head_len * notch_f, thickness
    )

    cr.move_to(*p0)
    cr.line_to(notch_x, notch_y)
    cr.stroke()


def draw_annotation(cr, a, arrow_style="classic"):
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
        draw_arrow(cr, a, arrow_style)
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


def render_surface(base_surface, annots, width, height, arrow_style="classic"):
    surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, width, height)
    cr = cairo.Context(surface)
    cr.set_source_surface(base_surface, 0, 0)
    cr.paint()
    for a in annots:
        draw_annotation(cr, a, arrow_style)
    return surface


def flatten(base_surface, annots, width, height, path, arrow_style="classic"):
    render_surface(base_surface, annots, width, height, arrow_style).write_to_png(path)
