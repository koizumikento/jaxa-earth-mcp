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
    assert [tool.name for tool in result.tools] == ["get_ndvi_anomaly"]
    assert result.tools[0].annotations and result.tools[0].annotations.read_only_hint


@pytest.mark.asyncio
async def test_map_and_validation(monkeypatch: pytest.MonkeyPatch) -> None:
    png = b64encode(b"\x89PNG\r\n\x1a\n").decode("ascii")

    def fake_render(month: str, bbox: list[float]) -> dict:
        assert bbox == [138.5, 36, 139.5, 37]
        return {"month": month, "statistics": {"mean": 0.012}, "png": png}

    monkeypatch.setattr("jaxa_earth_mcp.server.render_anomaly", fake_render)
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
