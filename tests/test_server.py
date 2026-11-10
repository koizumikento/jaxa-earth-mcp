import sys
from base64 import b64encode

import pytest
from mcp import Client, StdioServerParameters
from mcp.types import ImageContent

from jaxa_earth_mcp import create_server


@pytest.mark.asyncio
async def test_stdio_tools() -> None:
    params = StdioServerParameters(command=sys.executable, args=["-m", "jaxa_earth_mcp"])
    async with Client(params, mode="legacy", read_timeout_seconds=10) as client:
        result = await client.list_tools()
    assert {tool.name for tool in result.tools} == {
        "get_ndvi_anomaly",
        "get_ndvi_time_series",
        "search_collections",
    }
    assert all(tool.annotations and tool.annotations.read_only_hint for tool in result.tools)


@pytest.mark.asyncio
async def test_map_and_validation(monkeypatch: pytest.MonkeyPatch) -> None:
    png = b64encode(b"\x89PNG\r\n\x1a\n").decode("ascii")

    def fake_render(month: str, bbox: list[float]) -> dict:
        assert bbox == [138.5, 36, 139.5, 37]
        return {"month": month, "statistics": {"mean": 0.012}, "png": png}

    monkeypatch.setattr("jaxa_earth_mcp.client.render_anomaly", fake_render)
    async with Client(create_server()) as client:
        result = await client.call_tool(
            "get_ndvi_anomaly", {"month": "2021-08", "bbox": [138.5, 36, 139.5, 37]}
        )
        invalid = await client.call_tool(
            "get_ndvi_anomaly", {"month": "2021-08", "bbox": [139.5, 36, 138.5, 37]}
        )
    assert not result.is_error
    assert result.structured_content == {"month": "2021-08", "statistics": {"mean": 0.012}}
    assert isinstance(result.content[1], ImageContent)
    assert result.content[1].data == png
    assert invalid.is_error


@pytest.mark.asyncio
async def test_discovery_tools(monkeypatch: pytest.MonkeyPatch) -> None:
    def worker(operation, _error, *args):
        return {"operation": operation, "arguments": args}

    monkeypatch.setattr("jaxa_earth_mcp.client._run_worker", worker)
    bbox = [138.5, 36, 138.7, 36.2]
    async with Client(create_server()) as client:
        series = await client.call_tool(
            "get_ndvi_time_series",
            {"start_month": "2021-07", "end_month": "2021-08", "bbox": bbox},
        )
        catalog = await client.call_tool("search_collections", {"query": "ndvi"})
    assert not series.is_error
    assert series.structured_content == {
        "operation": "time_series",
        "arguments": [["2021-07", "2021-08"], bbox],
    }
    assert not catalog.is_error
    assert catalog.structured_content == {
        "operation": "collections",
        "arguments": ["ndvi", 5, 0],
    }
