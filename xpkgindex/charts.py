"""Build-time SVG charts.

Charts are generated as inline SVG rather than handed to a JS charting
library: no runtime dependency, no layout shift, and both themes can be
controlled exactly via `currentColor` and CSS custom properties.
"""

from __future__ import annotations

import datetime
from typing import Dict, List, Tuple

from .models import GrowthPoint, GrowthSeries as _Series


def _align(points, reference):
    """Pad a series onto the reference date axis.

    Series are built from the same daily snapshots, so this is a safety net
    for a caller that supplies fewer points rather than a routine transform.
    """
    if len(points) == len(reference):
        return points
    by_date = {p.date: p for p in points}
    out, last = [], 0
    for ref in reference:
        hit = by_date.get(ref.date)
        if hit is not None:
            last = hit.count
        out.append(GrowthPoint(date=ref.date, count=last))
    return out


def _time_positions(points: List[GrowthPoint]) -> List[float]:
    """Fractional x position of each point on a real time axis.

    Spacing by index would compress busy months and stretch quiet ones — the
    curve would encode commit cadence rather than elapsed time, and month
    labels would collide wherever activity clustered.
    """
    try:
        days = [datetime.date.fromisoformat(p.date).toordinal() for p in points]
    except ValueError:
        return [i / max(1, len(points) - 1) for i in range(len(points))]
    span = days[-1] - days[0]
    if span <= 0:
        return [0.0 for _ in points] if len(points) == 1 else \
               [i / (len(points) - 1) for i in range(len(points))]
    return [(d - days[0]) / span for d in days]


def growth_chart(series, width: int = 760, height: int = 220,
                 pad_left: int = 34, pad_bottom: int = 22, pad_top: int = 12,
                 gradient_id: str = "growth") -> Dict[str, object]:
    """Cumulative package count over time.

    `series[0]` is the total: it owns the date axis, the y scale and the
    filled area. Any further series are drawn as plain lines on top, so the
    chart reads as "of this whole, these parts" rather than as unrelated
    curves sharing an axis.
    """
    if not series:
        return {}
    if isinstance(series[0], GrowthPoint):      # single-series callers
        series = [_Series("all", "all", list(series))]
    points = series[0].points
    if not points:
        return {}

    inner_w = width - pad_left - 8
    inner_h = height - pad_bottom - pad_top
    n = len(points)
    top = max(p.count for p in points) or 1
    # Round the axis up to a friendly step so gridlines read cleanly.
    step = 10 ** max(0, len(str(top)) - 2)
    ceiling = ((top // (step * 5)) + 1) * step * 5 if top > 5 else top + 1

    frac = _time_positions(points)

    def x(i: int) -> float:
        return pad_left + inner_w * frac[i]

    def y(v: int) -> float:
        return pad_top + inner_h - (inner_h * v / ceiling)

    def path_for(pts) -> str:
        return " ".join(("M" if i == 0 else "L") + f"{x(i):.1f},{y(p.count):.1f}"
                        for i, p in enumerate(pts))

    line = path_for(points)
    area = f"{line} L{x(n - 1):.1f},{y(0):.1f} L{x(0):.1f},{y(0):.1f} Z"

    lines = []
    for i, s in enumerate(series):
        if s.color:
            color = s.color
        elif s.tone:
            color = f"var(--tone-{s.tone})"
        elif i == 0:
            color = "var(--tone-accent)"
        else:
            color = f"var(--series-{i})"
        pts = s.points if i == 0 else _align(s.points, points)
        lines.append({
            "key": s.key, "label": s.label, "color": color,
            "path": path_for(pts), "value": pts[-1].count if pts else 0,
            "last": {"x": round(x(len(pts) - 1), 1) if pts else 0,
                     "y": round(y(pts[-1].count), 1) if pts else 0},
        })

    ticks = []
    for k in range(0, 6):
        v = round(ceiling * k / 5)
        ticks.append({"y": round(y(v), 1), "label": str(v)})

    labels = []
    seen = set()
    for i, p in enumerate(points):
        month = p.date[:7]
        if month not in seen:
            seen.add(month)
            labels.append({"x": round(x(i), 1), "label": month})
    # Thin by pixel distance, not by count: after switching to a time axis the
    # labels are unevenly spaced, so "every Nth" can still collide.
    min_gap = 58
    kept = []
    for label in labels:
        if not kept or label["x"] - kept[-1]["x"] >= min_gap:
            kept.append(label)
    if kept and width - 8 - kept[-1]["x"] < min_gap / 2:
        kept.pop()
    labels = kept

    return {
        "width": width, "height": height,
        "line": line, "area": area, "lines": lines,
        "multi": len(lines) > 1,
        "ticks": ticks, "labels": labels,
        "gradient_id": gradient_id,
        "last": {"x": round(x(n - 1), 1), "y": round(y(points[-1].count), 1),
                 "value": points[-1].count},
        "first_date": points[0].date, "last_date": points[-1].date,
    }


def sparkline(points: List[GrowthPoint], width: int = 220, height: int = 54,
              gradient_id: str = "spark") -> Dict[str, object]:
    """Compact variant for the homepage pulse band / sidebars."""
    if not points:
        return {}
    n = len(points)
    top = max(p.count for p in points) or 1
    frac = _time_positions(points)

    def x(i: int) -> float:
        return width * frac[i]

    def y(v: int) -> float:
        return height - 3 - (height - 8) * v / top

    line = " ".join(("M" if i == 0 else "L") + f"{x(i):.1f},{y(p.count):.1f}"
                    for i, p in enumerate(points))
    area = f"{line} L{width},{height} L0,{height} Z"
    return {"width": width, "height": height, "line": line, "area": area,
            "gradient_id": gradient_id,
            "last": {"x": round(x(n - 1), 1), "y": round(y(points[-1].count), 1)}}
