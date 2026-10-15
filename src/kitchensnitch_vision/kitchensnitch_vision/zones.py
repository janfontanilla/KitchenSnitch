"""Helpers for normalized zones. A zone is [x, y, w, h], each in 0..1 of the frame."""
from typing import Sequence, Tuple


def in_zone(point: Tuple[float, float], zone: Sequence[float]) -> bool:
    x, y = point
    zx, zy, zw, zh = zone
    return zx <= x <= zx + zw and zy <= y <= zy + zh


def zone_to_rect(zone: Sequence[float], width: int, height: int) -> Tuple[int, int, int, int]:
    """Pixel rect (x0, y0, x1, y1), clamped to the frame and at least 1 px wide and tall."""
    zx, zy, zw, zh = zone
    x0 = min(max(int(zx * width), 0), width - 1)
    y0 = min(max(int(zy * height), 0), height - 1)
    x1 = min(max(int((zx + zw) * width), x0 + 1), width)
    y1 = min(max(int((zy + zh) * height), y0 + 1), height)
    return x0, y0, x1, y1
