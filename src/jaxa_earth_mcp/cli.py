import asyncio
import json
import sys
from argparse import SUPPRESS, ArgumentParser
from collections.abc import Sequence
from pathlib import Path

from .client import NdviAnomaly, get_ndvi_anomaly, get_ndvi_time_series, search_collections


def run_cli(argv: Sequence[str]) -> None:
    parser = ArgumentParser(prog="jaxa-earth-mcp")
    commands = parser.add_subparsers(required=True)

    command = commands.add_parser(
        "get-ndvi-anomaly",
        help="Get NDVI anomaly statistics and optionally save the PNG.",
        argument_default=SUPPRESS,
    )
    command.add_argument("--month", required=True)
    command.add_argument(
        "--bbox", type=float, nargs=4, metavar=("WEST", "SOUTH", "EAST", "NORTH"), required=True
    )
    command.add_argument("--output", type=Path, help="Save PNG to a new file.")
    command.set_defaults(handler=get_ndvi_anomaly)

    command = commands.add_parser(
        "get-ndvi-time-series", help="Get observed monthly NDVI statistics."
    )
    command.add_argument("--start-month", required=True)
    command.add_argument("--end-month", required=True)
    command.add_argument(
        "--bbox", type=float, nargs=4, metavar=("WEST", "SOUTH", "EAST", "NORTH"), required=True
    )
    command.set_defaults(handler=get_ndvi_time_series)

    command = commands.add_parser(
        "search-collections", help="Search collection IDs and list available bands."
    )
    command.add_argument("--query", required=True)
    command.add_argument("--limit", type=int, default=5)
    command.add_argument("--offset", type=int, default=0)
    command.set_defaults(handler=search_collections)

    arguments = vars(parser.parse_args(argv))
    handler = arguments.pop("handler")
    output = arguments.pop("output", None)
    try:
        result = asyncio.run(handler(**arguments))
        if isinstance(result, NdviAnomaly) and output is not None:
            with output.open("xb") as file:
                file.write(result.png)
        payload = result.metadata if isinstance(result, NdviAnomaly) else result
    except (ValueError, OSError) as exc:
        parser.exit(1, f"{parser.prog}: {exc}\n")
    sys.stdout.buffer.write((json.dumps(payload, ensure_ascii=False) + "\n").encode("utf-8"))
