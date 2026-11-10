import json
import subprocess
import sys
from asyncio import to_thread
from base64 import b64decode
from datetime import date
from typing import Annotated, Any, NamedTuple

from pydantic import Field, StringConstraints, validate_call

Month = Annotated[str, Field(pattern=r"^[0-9]{4}-(0[1-9]|1[0-2])$")]
Bounds = Annotated[list[float], Field(min_length=4, max_length=4)]
CatalogQuery = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)
]
CatalogLimit = Annotated[int, Field(ge=1, le=10)]
CatalogOffset = Annotated[int, Field(ge=0)]


def _run_worker(operation: str, error_message: str, *arguments: Any) -> dict[str, Any]:
    try:
        result = subprocess.run(
            [sys.executable, "-m", "jaxa_earth_mcp.render", operation, json.dumps(arguments)],
            capture_output=True,
            encoding="utf-8",
            errors="replace",
            timeout=90,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        raise ValueError("JAXA Earth image processing exceeded 90 seconds.") from exc
    if result.returncode != 0:
        raise ValueError(error_message)
    return json.loads(result.stdout)


def render_anomaly(month: str, bbox: list[float]) -> dict[str, Any]:
    return _run_worker(
        "anomaly", "JAXA Earth could not generate a map for this month and region.", month, bbox
    )


class NdviAnomaly(NamedTuple):
    """NDVI anomaly metadata and PNG bytes."""

    metadata: dict[str, Any]
    png: bytes


def _validate_bbox(bbox: list[float]) -> None:
    west, south, east, north = bbox
    if not (
        -180 <= west < east <= 180
        and -90 <= south < north <= 90
        and 0.2 <= round(east - west, 9) <= 5
        and 0.2 <= round(north - south, 9) <= 5
    ):
        raise ValueError("Provide an ordered bbox spanning 0.2 to 5 degrees in each dimension.")


@validate_call
async def get_ndvi_anomaly(month: Month, bbox: Bounds) -> NdviAnomaly:
    """Return a monthly NDVI anomaly map and statistics against the same-month normal.

    Use YYYY-MM and a WGS84 bounding box [west, south, east, north].
    """
    date.fromisoformat(f"{month}-01")
    _validate_bbox(bbox)
    rendered = await to_thread(render_anomaly, month, bbox)
    image = b64decode(rendered.pop("png"), validate=True)
    return NdviAnomaly(metadata=rendered, png=image)


@validate_call
async def get_ndvi_time_series(
    start_month: Month, end_month: Month, bbox: Bounds
) -> dict[str, Any]:
    """Return observed MODIS NDVI statistics for every month in an inclusive date range.

    Use YYYY-MM, up to 12 months and a WGS84 bounding box [west, south, east, north].
    Each month has a status and either statistics or null if observations are missing.
    """
    start = date.fromisoformat(f"{start_month}-01")
    end = date.fromisoformat(f"{end_month}-01")
    first = 12 * start.year + start.month - 1
    last = 12 * end.year + end.month - 1
    if not 0 <= last - first < 12:
        raise ValueError("Provide an ordered date range spanning 1 to 12 months inclusive.")
    _validate_bbox(bbox)
    months = [f"{index // 12:04d}-{index % 12 + 1:02d}" for index in range(first, last + 1)]
    return await to_thread(
        _run_worker,
        "time_series",
        "JAXA Earth could not retrieve NDVI observations for the requested months and region.",
        months,
        bbox,
    )


@validate_call
async def search_collections(
    query: CatalogQuery, limit: CatalogLimit = 5, offset: CatalogOffset = 0
) -> dict[str, Any]:
    """Search official JAXA Earth collection IDs and return available bands.

    All space-separated terms must occur in the ID, ignoring case. Use next_offset
    to get the next page. No raster imagery is downloaded.
    """
    return await to_thread(
        _run_worker,
        "collections",
        "JAXA Earth could not retrieve the collection catalog.",
        query,
        limit,
        offset,
    )
