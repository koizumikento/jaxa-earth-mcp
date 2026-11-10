from types import SimpleNamespace

import pytest
from jaxa.earth import je

from jaxa_earth_mcp import get_ndvi_time_series, search_collections
from jaxa_earth_mcp.render import OBSERVED, observed_time_series
from jaxa_earth_mcp.render import search_collections as search_catalog


@pytest.mark.asyncio
async def test_public_inputs(monkeypatch: pytest.MonkeyPatch) -> None:
    calls = []

    def worker(operation, _error, *args):
        calls.append((operation, args))
        return {}

    monkeypatch.setattr("jaxa_earth_mcp.client._run_worker", worker)
    bbox = [138.5, 36, 138.7, 36.2]
    await get_ndvi_time_series("2020-12", "2021-02", bbox)
    await search_collections(" ndvi monthly ", 2, 1)
    for start, end, bounds in [
        ("2021-08", "2021-07", bbox),
        ("2020-07", "2021-07", bbox),
        ("2021-00", "2021-07", bbox),
        ("2021-07", "2021-07", [139.0, 36.0, 138.0, 37.0]),
    ]:
        with pytest.raises(ValueError):
            await get_ndvi_time_series(start, end, bounds)
    with pytest.raises(ValueError):
        await search_collections(" ")
    with pytest.raises(ValueError):
        await search_collections("ndvi", 11)
    with pytest.raises(ValueError):
        await search_collections("ndvi", 2, -1)
    assert calls == [
        ("time_series", (["2020-12", "2021-01", "2021-02"], bbox)),
        ("collections", ("ndvi monthly", 2, 1)),
    ]


def test_ndvi_statistics_stay_with_their_month(monkeypatch: pytest.MonkeyPatch) -> None:
    bbox = [138.5, 36, 138.7, 36.2]

    class Collection:
        month = ""

        def filter_date(self, *, dlim):
            self.month = dlim[0][:7]
            assert dlim == [f"{self.month}-01T00:00:00"] * 2
            if self.month == "2021-02":
                raise Exception("Error! No date list found!")
            if self.month == "2021-06":
                raise RuntimeError("network unavailable")
            return self

        def filter_resolution(self, *, ppu):
            assert ppu == 24
            return self

        def filter_bounds(self, *, bbox):
            if self.month == "2021-03":
                raise Exception(f"Error! No COGs in bounds found!\nbbox : {bbox}")
            return self

        def select(self, band):
            assert band == "ndvi"
            return self

        def get_images(self):
            return self

    def get_collection(identifier, *, ssl_verify):
        assert identifier == OBSERVED
        assert ssl_verify
        return Collection()

    def process(images):
        def spatial_stats():
            value = {"2021-01": 0.1, "2021-04": float("nan"), "2021-05": 0.5}[images.month]
            return SimpleNamespace(
                timeseries={"mean": SimpleNamespace(item=lambda: value)},
            )

        return SimpleNamespace(calc_spatial_stats=spatial_stats)

    monkeypatch.setattr(je, "ImageCollection", get_collection)
    monkeypatch.setattr(je, "ImageProcess", process)
    result = observed_time_series([f"2021-{month:02d}" for month in range(1, 6)], bbox)
    assert result["observations"] == [
        {"month": "2021-01", "status": "observed", "statistics": {"mean": 0.1}},
        {"month": "2021-02", "status": "not_available", "statistics": None},
        {"month": "2021-03", "status": "no_coverage", "statistics": None},
        {"month": "2021-04", "status": "no_valid_pixels", "statistics": None},
        {"month": "2021-05", "status": "observed", "statistics": {"mean": 0.5}},
    ]
    with pytest.raises(RuntimeError, match="network unavailable"):
        observed_time_series(["2021-06"], bbox)


def test_catalog_only_loads_bands_for_the_requested_page(monkeypatch: pytest.MonkeyPatch) -> None:
    fetched = []

    def catalog(*, ssl_verify):
        assert ssl_verify
        return SimpleNamespace(
            stac_collections=SimpleNamespace(
                id=["Z_NDVI_monthly", "a_ndvi_monthly", "A_NDVI_daily", "b_ndvi_monthly"]
            )
        )

    def collection(identifier, *, ssl_verify):
        assert ssl_verify
        fetched.append(identifier)
        return SimpleNamespace(
            stac_collection=SimpleNamespace(
                json=[[{"assets": {"ndvi": {}}}]], url=[["https://example.test/collection.json"]]
            )
        )

    monkeypatch.setattr(je, "ImageCollectionList", catalog)
    monkeypatch.setattr(je, "ImageCollection", collection)
    page = search_catalog("NDVI monthly", 1, 1)
    assert page["total"] == 3
    assert page["next_offset"] == 2
    assert page["collections"] == [
        {
            "id": "b_ndvi_monthly",
            "bands": ["ndvi"],
            "catalog_url": "https://example.test/collection.json",
        }
    ]
    assert search_catalog("NDVI monthly", 1, 3)["next_offset"] is None
    assert search_catalog("unknown", 1, 0)["collections"] == []
    assert fetched == ["b_ndvi_monthly"]
