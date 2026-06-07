"""Run a deterministic or local UDP telemetry probe."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from mavlink.client import (  # noqa: E402
    DEFAULT_UDP_PORT,
    TelemetryClientError,
    UdpTelemetryClient,
    iter_json_fixture_messages,
    run_telemetry_probe,
    telemetry_probe_to_json_dict,
    write_probe_json,
)


def main() -> int:
    parser = argparse.ArgumentParser()
    source_group = parser.add_mutually_exclusive_group(required=True)
    source_group.add_argument("--fixture-json", type=Path)
    source_group.add_argument("--udp-json", action="store_true")
    parser.add_argument("--udp-host", default="127.0.0.1")
    parser.add_argument("--udp-port", type=int, default=DEFAULT_UDP_PORT)
    parser.add_argument("--duration-s", type=float, default=5.0)
    parser.add_argument("--max-messages", type=int)
    parser.add_argument("--source-label")
    parser.add_argument("--write-json", type=Path)
    args = parser.parse_args()
    if args.udp_json and args.write_json is not None:
        parser.error(
            "--udp-json --write-json is disabled because UDP probe timestamps "
            "are runtime-derived; use stdout for ad hoc debugging"
        )
    if args.fixture_json is not None and not args.fixture_json.is_file():
        parser.error(f"--fixture-json must point to a readable file: {args.fixture_json}")

    try:
        if args.fixture_json is not None:
            messages = iter_json_fixture_messages(args.fixture_json)
            source = args.source_label or f"fixture:{args.fixture_json.name}"
            use_wall_clock_probe_end = False
            transport_error_provider = None
        else:
            client = UdpTelemetryClient(host=args.udp_host, port=args.udp_port)
            messages = client.iter_messages(
                duration_s=args.duration_s,
                max_messages=args.max_messages,
            )
            source = args.source_label or f"udp-json:{args.udp_host}:{args.udp_port}"
            use_wall_clock_probe_end = True
            transport_error_provider = client.transport_errors

        run = run_telemetry_probe(
            messages,
            source=source,
            use_wall_clock_probe_end=use_wall_clock_probe_end,
            transport_error_provider=transport_error_provider,
        )
    except TelemetryClientError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    if args.write_json is not None:
        write_probe_json(args.write_json, run)
    else:
        print(json.dumps(telemetry_probe_to_json_dict(run), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
