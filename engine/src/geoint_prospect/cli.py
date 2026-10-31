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
from geoint_prospect.storage.keys import InvalidObjectKey
from geoint_prospect.storage.providers import StorageError, build_providers
from geoint_prospect.storage.publish import summarise
from geoint_prospect.storage.smoke import smoke_key, smoke_test


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
    run.add_argument("--source-id", help="registered source for ingestion pipelines")
    run.add_argument(
        "--publish",
        default="",
        help="persistent storage providers, e.g. 'b2' or 'b2,filebase' (default: publish nothing)",
    )
    run.add_argument(
        "--store-raw",
        action="store_true",
        help="also publish the acquired raw file (ingestion pipelines)",
    )
    run.add_argument(
        "--dry-run", action="store_true", help="validate the request without processing"
    )
    run.add_argument("--json", action="store_true", help="wrap the answer in the JSON envelope")

    storage = commands.add_parser("storage", help="storage operations")
    storage.add_argument("action", choices=["smoke"])
    storage.add_argument("--providers", required=True, help="e.g. 'b2' or 'b2,filebase'")
    storage.add_argument("--request-id", required=True)
    storage.add_argument("--keep", action="store_true", help="leave the test object in place")
    storage.add_argument(
        "--dry-run", action="store_true", help="validate provider configuration only"
    )
    storage.add_argument("--json", action="store_true", help="wrap the answer in the JSON envelope")
    return parser


def _emit(payload: dict[str, object], *, as_json: bool, exit_code: int) -> int:
    if as_json:
        print(json.dumps(payload))
    elif payload["ok"]:
        print(json.dumps(payload["data"], indent=2))
    else:
        print(f"error: {payload['error']}", file=sys.stderr)
    return exit_code


def _storage_command(args: argparse.Namespace) -> dict[str, object]:
    """`storage smoke`: prove upload + read-back with the configured providers."""
    providers = build_providers(args.providers)
    selected = [provider.config.provider.value for provider in providers]

    if args.dry_run:
        return {
            "action": "smoke",
            "dry_run": True,
            "request_id": args.request_id,
            "providers": selected,
            "key": smoke_key(args.request_id),
        }

    results = smoke_test(providers, args.request_id, keep=args.keep)
    summary = summarise(results)
    if not summary["ok"]:
        raise StorageError(f"smoke test failed: {', '.join(summary['failed'])}")  # type: ignore[arg-type]

    verified = [result for result in results if result.verified]
    if len(verified) != len(results):  # pragma: no cover - defensive, summarise already fails
        raise StorageError("smoke test did not verify every provider")

    return {
        "action": "smoke",
        "request_id": args.request_id,
        "providers": selected,
        "kept": args.keep,
        "results": [result.model_dump() for result in results],
        "summary": summary,
    }


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)

    try:
        if args.command == "pipelines":
            data = {
                "pipelines": [{"name": name, "implemented": True} for name in sorted(PIPELINES)]
            }
        elif args.command == "storage":
            data = _storage_command(args)
        else:
            request = RunRequest(
                pipeline=args.pipeline,
                request_id=args.request_id,
                input=args.input,
                output=args.output,
                dataset_id=args.dataset_id,
                source_id=args.source_id,
                publish=args.publish,
                store_raw=args.store_raw,
                dry_run=args.dry_run,
            )
            data = execute(request)
    except (PipelineError, StorageError, InvalidObjectKey) as exc:
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
