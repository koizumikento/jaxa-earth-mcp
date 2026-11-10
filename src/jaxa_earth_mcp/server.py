import json
from base64 import b64encode

from mcp.server import MCPServer
from mcp.types import CallToolResult, ImageContent, TextContent, ToolAnnotations

from .client import Bounds, Month
from .client import get_ndvi_anomaly as fetch_ndvi_anomaly

READ_ONLY = ToolAnnotations(
    read_only_hint=True, idempotent_hint=True, destructive_hint=False, open_world_hint=True
)


def create_server() -> MCPServer:
    mcp = MCPServer("jaxa-earth-mcp")

    @mcp.tool(annotations=READ_ONLY)
    async def get_ndvi_anomaly(month: Month, bbox: Bounds) -> CallToolResult:
        """Return a monthly NDVI anomaly map and statistics against the same-month normal.

        Use YYYY-MM and a WGS84 bounding box [west, south, east, north].
        """
        result = await fetch_ndvi_anomaly(month, bbox)
        return CallToolResult(
            content=[
                TextContent(type="text", text=json.dumps(result.metadata, ensure_ascii=False)),
                ImageContent(
                    type="image", data=b64encode(result.png).decode("ascii"), mime_type="image/png"
                ),
            ],
            structured_content=result.metadata,
        )

    return mcp
