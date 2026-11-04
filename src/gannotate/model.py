"""Pure annotation model: geometry, hit-testing and transforms."""

import copy
import math


def dist_to_segment(p, a, b):
    """Distance from point p to the segment a-b."""
    ax, ay = a
    bx, by = b
    px, py = p
    dx, dy = bx - ax, by - ay
    if dx == 0 and dy == 0:
        return math.hypot(px - ax, py - ay)
    t = ((px - ax) * dx + (py - ay) * dy) / (dx * dx + dy * dy)
    t = max(0.0, min(1.0, t))
    return math.hypot(px - (ax + t * dx), py - (ay + t * dy))


def transform_point(p, sx, sy, ax, ay):
    return (ax + (p[0] - ax) * sx, ay + (p[1] - ay) * sy)


def bbox(a):
    """Bounding box of an annotation in image coordinates."""
    kind = a["type"]
    if kind in ("pen", "mark"):
        xs = [p[0] for p in a["points"]]
        ys = [p[1] for p in a["points"]]
        x0, x1, y0, y1 = min(xs), max(xs), min(ys), max(ys)
        pad = a["width"] / 2.0
    elif kind == "text":
        x0, y0 = a["p0"]
        x1, y1 = x0 + a["tw"], y0 + a["th"]
        pad = 2
    else:
        x0 = min(a["p0"][0], a["p1"][0])
        x1 = max(a["p0"][0], a["p1"][0])
        y0 = min(a["p0"][1], a["p1"][1])
        y1 = max(a["p0"][1], a["p1"][1])
        pad = a["width"] / 2.0
    return (x0 - pad, y0 - pad, x1 + pad, y1 + pad)


def hit(a, p, scale):
    """True if point p (image coords) hits annotation a."""
    kind = a["type"]
    if kind in ("rect", "ellipse", "text"):
        x0, y0, x1, y1 = bbox(a)
        return x0 <= p[0] <= x1 and y0 <= p[1] <= y1
    if kind in ("line", "arrow"):
        return dist_to_segment(p, a["p0"], a["p1"]) <= max(a["width"], 6) + 6 / scale
    if kind in ("pen", "mark"):
        pts = a["points"]
        threshold = max(a["width"], 6) + 6 / scale
        return any(
            dist_to_segment(p, pts[i], pts[i + 1]) <= threshold
            for i in range(len(pts) - 1)
        )
    return False


def translate(a, dx, dy):
    b = copy.deepcopy(a)
    if b["type"] in ("pen", "mark"):
        b["points"] = [(x + dx, y + dy) for x, y in b["points"]]
        b["p0"] = (b["p0"][0] + dx, b["p0"][1] + dy)
        b["p1"] = (b["p1"][0] + dx, b["p1"][1] + dy)
    elif "p1" in b:
        b["p0"] = (b["p0"][0] + dx, b["p0"][1] + dy)
        b["p1"] = (b["p1"][0] + dx, b["p1"][1] + dy)
    else:
        b["p0"] = (b["p0"][0] + dx, b["p0"][1] + dy)
    return b


def scale_annotation(a, sx, sy, ax, ay, measure_text):
    b = copy.deepcopy(a)
    if b["type"] in ("pen", "mark"):
        b["points"] = [transform_point(p, sx, sy, ax, ay) for p in b["points"]]
        b["p0"] = transform_point(b["p0"], sx, sy, ax, ay)
        b["p1"] = transform_point(b["p1"], sx, sy, ax, ay)
    elif "p1" in b:
        b["p0"] = transform_point(b["p0"], sx, sy, ax, ay)
        b["p1"] = transform_point(b["p1"], sx, sy, ax, ay)
    else:
        b["p0"] = transform_point(b["p0"], sx, sy, ax, ay)
    if b["type"] == "text":
        b["size"] = max(6.0, b["size"] * (sx + sy) / 2.0)
        b["tw"], b["th"] = measure_text(b["text"], b["size"])
    return b
