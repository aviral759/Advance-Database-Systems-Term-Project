"""EXIF / GPS extraction using Pillow's IFD API."""
from __future__ import annotations

import calendar
import math
from datetime import datetime

from PIL import Image

EXIF_IFD = 0x8769
GPS_IFD = 0x8825
_DT_FORMATS = ("%Y:%m:%d %H:%M:%S", "%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d")


def _clean(v):
    if v is None:
        return None
    if isinstance(v, bytes):
        v = v.decode("utf-8", "ignore")
    v = str(v).replace("\x00", "").strip()
    return v or None


def _num(v):
    if v is None:
        return None
    if isinstance(v, (tuple, list)):
        if len(v) == 2 and all(isinstance(x, (int, float)) for x in v):
            return v[0] / v[1] if v[1] else None
        v = v[0] if v else None
        if v is None:
            return None
    try:
        f = float(v)
    except (TypeError, ValueError, ZeroDivisionError):
        return None
    return f if math.isfinite(f) else None


def _dms(values, ref):
    if not values or len(values) != 3:
        return None
    parts = [_num(x) for x in values]
    if any(p is None for p in parts):
        return None
    d, m, s = parts
    val = d + m / 60.0 + s / 3600.0
    ref = _clean(ref)
    if ref and ref.upper() in ("S", "W"):
        val = -val
    return val


def parse_datetime(value) -> tuple[str | None, int | None]:
    """Return (ISO string, epoch seconds treating the wall-clock time as UTC)."""
    v = _clean(value)
    if not v:
        return None, None
    v = v[:19]
    for fmt in _DT_FORMATS:
        try:
            dt = datetime.strptime(v, fmt)
        except ValueError:
            continue
        return dt.isoformat(), calendar.timegm(dt.timetuple())
    return None, None


def extract_exif(img: Image.Image) -> dict:
    out: dict = {}
    try:
        exif = img.getexif()
    except Exception:
        return out
    if not exif:
        return out
    out["camera_make"] = _clean(exif.get(271))
    out["camera_model"] = _clean(exif.get(272))
    try:
        sub = exif.get_ifd(EXIF_IFD) or {}
    except Exception:
        sub = {}
    taken_at, taken_ts = parse_datetime(sub.get(36867) or sub.get(36868) or exif.get(306))
    out["taken_at"], out["taken_ts"] = taken_at, taken_ts
    out["f_number"] = _num(sub.get(33437))
    out["exposure_time"] = _num(sub.get(33434))
    iso = _num(sub.get(34855))
    out["iso"] = int(iso) if iso else None
    out["focal_length"] = _num(sub.get(37386))
    out["lens_model"] = _clean(sub.get(42036))
    try:
        gps = exif.get_ifd(GPS_IFD) or {}
    except Exception:
        gps = {}
    if gps:
        lat, lon = _dms(gps.get(2), gps.get(1)), _dms(gps.get(4), gps.get(3))
        if (lat is not None and lon is not None and -90 <= lat <= 90 and -180 <= lon <= 180
                and not (lat == 0 and lon == 0)):
            out["gps_lat"], out["gps_lon"] = round(lat, 7), round(lon, 7)
    return {k: v for k, v in out.items() if v is not None}