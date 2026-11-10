import json
import subprocess
import sys
from asyncio import to_thread
from base64 import b64decode
from datetime import date
from typing import Annotated, Any, NamedTuple

from pydantic import Field, validate_call

Month = Annotated[str, Field(pattern=r"^[0-9]{4}-(0[1-9]|1[0-2])$")]
Bounds = Annotated[list[float], Field(min_length=4, max_length=4)]


def render_anomaly(month: str, bbox: list[float]) -> dict[str, Any]:
    try:
        result = subprocess.run(
            [sys.executable, "-m", "jaxa_earth_mcp.render", month, json.dumps(bbox)],
            capture_output=True,
            encoding="utf-8",
            errors="replace",
            timeout=90,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        raise ValueError("JAXA Earth image processing exceeded 90 seconds.") from exc
    if result.returncode != 0:
        raise ValueError("JAXA Earth could not generate a map for this month and region.")
    return json.loads(result.stdout)


class NdviAnomaly(NamedTuple):
    """NDVI anomaly metadata and PNG bytes."""

    metadata: dict[str, Any]
    png: bytes


@validate_call
async def get_ndvi_anomaly(month: Month, bbox: Bounds) -> NdviAnomaly:
    """Return a monthly NDVI anomaly map and statistics against the same-month normal.

    Use YYYY-MM and a WGS84 bounding box [west, south, east, north].
    """
    date.fromisoformat(f"{month}-01")
    west, south, east, north = bbox
    if not (
        -180 <= west < east <= 180
        and -90 <= south < north <= 90
        and 0.2 <= round(east - west, 9) <= 5
        and 0.2 <= round(north - south, 9) <= 5
    ):
        raise ValueError("Provide an ordered bbox spanning 0.2 to 5 degrees in each dimension.")
    rendered = await to_thread(render_anomaly, month, bbox)
    image = b64decode(rendered.pop("png"), validate=True)
    return NdviAnomaly(metadata=rendered, png=image)
