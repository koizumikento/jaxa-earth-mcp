import json
import math
import sys
from base64 import b64encode
from contextlib import redirect_stdout
from typing import Any

import matplotlib

OBSERVED = "JAXA.JASMES_Terra.MODIS-Aqua.MODIS_ndvi.v811_global_monthly"
NORMAL = "JAXA.JASMES_Terra.MODIS-Aqua.MODIS_ndvi.v811_global_monthly-normal"


def render(month: str, bbox: list[float]) -> dict[str, Any]:
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
    values = {key: float(value.item()) for key, value in anomaly.timeseries.items()}
    if not math.isfinite(values["mean"]):
        raise ValueError("No valid NDVI pixels in the requested region.")
    image = anomaly.show_images(cmap="turbo", clim=[-0.3, 0.3], output="png_buffer")
    return {
        "month": month,
        "bbox": bbox,
        "baseline": "2012–2021 same calendar month",
        "operation": "observed NDVI minus climatological NDVI",
        "statistics": {
            key: value if math.isfinite(value) else None for key, value in values.items()
        },
        "datasets": [OBSERVED, NORMAL],
        "source": "Processed using JAXA Earth API for Python",
        "source_url": "https://data.earth.jaxa.jp/ja/",
        "png": b64encode(image.png_buffers[0]).decode("ascii"),
    }


if __name__ == "__main__":
    # The JAXA SDK prints progress while computing the raster.
    with redirect_stdout(sys.stderr):
        result = render(sys.argv[1], json.loads(sys.argv[2]))
    print(json.dumps(result, allow_nan=False))
