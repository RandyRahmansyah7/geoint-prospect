"""Command line contract for the engine.

The backend workflow and, later, the desktop app call exactly these commands:

    python -m geoint_prospect pipelines list [--json]
    python -m geoint_prospect run --pipeline <name> --request-id <id> [options]

Every answer is one JSON envelope: {"ok": bool, "data": ... | null, "error": ... | null}.
Exit codes: 0 success, 2 invalid request, 1 unexpected failure.
"""

import argparse
import json
import sys
from pathlib import Path

from geoint_prospect import __version__
from geoint_prospect.pipelines import PIPELINES, PipelineError, RunRequest, execute


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="geoint_prospect", description=__doc__)
    parser.add_argument("--version", action="version", version=__version__)
    commands = parser.add_subparsers(dest="command", required=True)

    pipelines = commands.add_parser("pipelines", help="inspect the registered pipelines")
    pipelines.add_argument("action", choices=["list"])
    pipelines.add_argument(
        "--json", action="store_true", help="wrap the answer in the JSON envelope"
    )

    run = commands.add_parser("run", help="run one registered pipeline")
    run.add_argument("--pipeline", required=True)
    run.add_argument("--request-id", required=True)
    run.add_argument("--input", type=Path)
    run.add_argument("--output", type=Path)
    run.add_argument("--dataset-id")
    run.add_argument(
        "--dry-run", action="store_true", help="validate the request without processing"
    )
    run.add_argument("--json", action="store_true", help="wrap the answer in the JSON envelope")
    return parser


def _emit(payload: dict[str, object], *, as_json: bool, exit_code: int) -> int:
    if as_json:
        print(json.dumps(payload))
    elif payload["ok"]:
        print(json.dumps(payload["data"], indent=2))
    else:
        print(f"error: {payload['error']}", file=sys.stderr)
    return exit_code


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)

    try:
        if args.command == "pipelines":
            data = {
                "pipelines": [{"name": name, "implemented": True} for name in sorted(PIPELINES)]
            }
        else:
            request = RunRequest(
                pipeline=args.pipeline,
                request_id=args.request_id,
                input=args.input,
                output=args.output,
                dataset_id=args.dataset_id,
                dry_run=args.dry_run,
            )
            data = execute(request)
    except PipelineError as exc:
        return _emit(
            {"ok": False, "data": None, "error": {"code": "invalid_request", "message": str(exc)}},
            as_json=args.json,
            exit_code=2,
        )
    except Exception as exc:  # noqa: BLE001 - the CLI is the boundary; report, never traceback at users
        return _emit(
            {"ok": False, "data": None, "error": {"code": "unexpected", "message": str(exc)}},
            as_json=args.json,
            exit_code=1,
        )

    return _emit({"ok": True, "data": data, "error": None}, as_json=args.json, exit_code=0)
