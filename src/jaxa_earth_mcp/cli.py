import asyncio
import json
import sys
from argparse import SUPPRESS, ArgumentParser
from collections.abc import Sequence
from pathlib import Path

from .client import get_ndvi_anomaly


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

    arguments = vars(parser.parse_args(argv))
    handler = arguments.pop("handler")
    output = arguments.pop("output", None)
    try:
        result = asyncio.run(handler(**arguments))
        if output is not None:
            with output.open("xb") as file:
                file.write(result.png)
        payload = result.metadata
    except (ValueError, OSError) as exc:
        parser.exit(1, f"{parser.prog}: {exc}\n")
    sys.stdout.buffer.write((json.dumps(payload, ensure_ascii=False) + "\n").encode("utf-8"))
