import json
from unittest.mock import AsyncMock

import pytest

from jaxa_earth_mcp import NdviAnomaly, cli


def test_cli_uses_public_function(
    monkeypatch: pytest.MonkeyPatch, capsysbinary: pytest.CaptureFixture[bytes], tmp_path
) -> None:
    payload = {"name": "日本語"}
    output = tmp_path / "anomaly.png"
    handler = AsyncMock(return_value=NdviAnomaly(metadata=payload, png=b"png"))
    monkeypatch.setattr(cli, "get_ndvi_anomaly", handler)
    args = ["get-ndvi-anomaly", "--month", "2021-08", "--bbox", "138.5", "36", "139.5", "37"]
    args.extend(["--output", str(output)])
    cli.run_cli(args)
    handler.assert_awaited_once_with(**{"month": "2021-08", "bbox": [138.5, 36, 139.5, 37]})
    assert json.loads(capsysbinary.readouterr().out) == payload
    assert output.read_bytes() == b"png"
    with pytest.raises(SystemExit):
        cli.run_cli(args)
    assert output.read_bytes() == b"png"
