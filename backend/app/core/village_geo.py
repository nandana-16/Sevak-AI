"""Synthetic village -> (lat, lng) lookup, scattered around a Pune-district-like
bounding box in Maharashtra (matches the SRS's stated pilot geography). Used only
to make the dashboard heatmap demonstrable without a real GIS/geocoding dependency."""
import hashlib

BASE_LAT, BASE_LNG = 18.52, 73.85  # Pune, Maharashtra
SPREAD = 0.9


def village_coords(village: str) -> tuple[float, float]:
    h = hashlib.md5(village.encode()).hexdigest()
    lat_offset = (int(h[:8], 16) / 0xFFFFFFFF - 0.5) * SPREAD
    lng_offset = (int(h[8:16], 16) / 0xFFFFFFFF - 0.5) * SPREAD
    return round(BASE_LAT + lat_offset, 5), round(BASE_LNG + lng_offset, 5)
