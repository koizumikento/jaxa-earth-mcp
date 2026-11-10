import json
import math
import sys
from base64 import b64encode
from contextlib import redirect_stdout
from typing import Any

OBSERVED = "JAXA.JASMES_Terra.MODIS-Aqua.MODIS_ndvi.v811_global_monthly"
NORMAL = "JAXA.JASMES_Terra.MODIS-Aqua.MODIS_ndvi.v811_global_monthly-normal"
SOURCE_URL = "https://data.earth.jaxa.jp/ja/"


def _finite_statistics(timeseries: dict[str, Any]) -> dict[str, float | None]:
    values = {key: float(value.item()) for key, value in timeseries.items()}
    return {key: value if math.isfinite(value) else None for key, value in values.items()}


def render(month: str, bbox: list[float]) -> dict[str, Any]:
    import matplotlib

    matplotlib.use("Agg")
    from jaxa.earth import je

    timestamp = f"{month}-01T00:00:00"

    def fetch(dataset: str, band: str) -> Any:
        return (
            je.ImageCollection(dataset, ssl_verify=True)
            .filter_date(dlim=[timestamp, timestamp])
            .filter_resolution(ppu=24)
            .filter_bounds(bbox=bbox)
            .select(band)
            .get_images()
        )

    observed = fetch(OBSERVED, "ndvi")
    normal = fetch(NORMAL, "ndvi_2012_2021")
    anomaly = je.ImageProcess(observed).diff_images(normal).calc_spatial_stats()
    statistics = _finite_statistics(anomaly.timeseries)
    if statistics["mean"] is None:
        raise ValueError("No valid NDVI pixels in the requested region.")
    # The SDK uses the collection label as the image title.
    anomaly.collection = "JAXA Earth API | NDVI anomaly vs 2012-2021 normal"
    image = anomaly.show_images(cmap="turbo", clim=[-0.3, 0.3], output="png_buffer")
    return {
        "month": month,
        "bbox": bbox,
        "baseline": "2012–2021 same calendar month",
        "operation": "observed NDVI minus climatological NDVI",
        "statistics": statistics,
        "datasets": [OBSERVED, NORMAL],
        "source": "Processed using JAXA Earth API for Python",
        "source_url": SOURCE_URL,
        "png": b64encode(image.png_buffers[0]).decode("ascii"),
    }


def observed_time_series(months: list[str], bbox: list[float]) -> dict[str, Any]:
    from jaxa.earth import je

    collection = je.ImageCollection(OBSERVED, ssl_verify=True)
    observations = []
    # The SDK can omit dates with no tiles. Filter each month so statistics keep their date.
    # The pinned SDK signals an empty date or bounds filter with a generic exception.
    for month in months:
        timestamp = f"{month}-01T00:00:00"
        statistics = None
        try:
            images = (
                collection.filter_date(dlim=[timestamp, timestamp])
                .filter_resolution(ppu=24)
                .filter_bounds(bbox=bbox)
                .select("ndvi")
                .get_images()
            )
        except Exception as exc:
            message = str(exc)
            if message == "Error! No date list found!":
                status = "not_available"
            elif message.startswith("Error! No COGs in bounds found!\n"):
                status = "no_coverage"
            else:
                raise
        else:
            values = _finite_statistics(je.ImageProcess(images).calc_spatial_stats().timeseries)
            if values["mean"] is None:
                status = "no_valid_pixels"
            else:
                statistics = values
                status = "observed"
        observations.append({"month": month, "status": status, "statistics": statistics})

    return {
        "bbox": bbox,
        "dataset": OBSERVED,
        "band": "ndvi",
        "observations": observations,
        "source": "Processed using JAXA Earth API for Python",
        "source_url": SOURCE_URL,
    }


def search_collections(query: str, limit: int, offset: int) -> dict[str, Any]:
    from jaxa.earth import je

    terms = query.casefold().split()
    # Filter IDs before loading per-collection band metadata to bound upstream requests.
    catalog = je.ImageCollectionList(ssl_verify=True).stac_collections
    matching = sorted(
        (
            identifier
            for identifier in catalog.id
            if all(term in identifier.casefold() for term in terms)
        ),
        key=str.casefold,
    )
    collections = []
    for identifier in matching[offset : offset + limit]:
        collection = je.ImageCollection(identifier, ssl_verify=True).stac_collection
        collections.append(
            {
                "id": identifier,
                "bands": list(collection.json[0][0]["assets"]),
                "catalog_url": collection.url[0][0],
            }
        )
    next_offset = offset + len(collections)
    return {
        "collections": collections,
        "total": len(matching),
        "next_offset": next_offset if next_offset < len(matching) else None,
        "source_url": SOURCE_URL,
    }


if __name__ == "__main__":
    # The JAXA SDK prints progress while retrieving collections and computing rasters.
    operations = {
        "anomaly": render,
        "time_series": observed_time_series,
        "collections": search_collections,
    }
    with redirect_stdout(sys.stderr):
        result = operations[sys.argv[1]](*json.loads(sys.argv[2]))
    print(json.dumps(result, allow_nan=False))
