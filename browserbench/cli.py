from __future__ import annotations

import argparse
from pathlib import Path

from .config import load_config
from .har_analysis import analyze_paths, write_mime_csv, write_run_csv, write_summary_csv
from .manifest import build_manifest, write_manifest
from .page_metrics_analysis import (
    analyze_paths as analyze_page_metric_paths,
    write_run_csv as write_page_metrics_csv,
    write_summary_csv as write_page_metrics_summary_csv,
)
from .runner import run_manifest
from .server import serve


def _discover_har_paths(root: Path) -> list[Path]:
    if root.is_file():
        return [root]
    return sorted(root.rglob("*.har"))


def _discover_json_paths(root: Path) -> list[Path]:
    if root.is_file():
        return [root]
    return sorted(root.rglob("*.json"))


def main() -> None:
    parser = argparse.ArgumentParser(description="Browser network benchmark utilities.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    serve_parser = subparsers.add_parser("serve", help="Serve benchmark scenarios locally.")
    serve_parser.add_argument("--host", default="127.0.0.1")
    serve_parser.add_argument("--port", type=int, default=8000)
    serve_parser.add_argument(
        "--scenario-root",
        type=Path,
        default=Path("scenarios"),
        help="Directory containing scenario pages.",
    )

    manifest_parser = subparsers.add_parser("write-manifest", help="Generate a run manifest from TOML config.")
    manifest_parser.add_argument("config", type=Path)

    run_parser = subparsers.add_parser("run-manifest", help="Execute a manifest with the experimental Playwright harness.")
    run_parser.add_argument("manifest", type=Path)
    run_parser.add_argument("--post-load-wait-ms", type=int, default=1000)
    run_parser.add_argument("--no-trace", action="store_true")

    analyze_parser = subparsers.add_parser("analyze-har", help="Analyze HAR artifacts and write CSV outputs.")
    analyze_parser.add_argument("har_root", type=Path)
    analyze_parser.add_argument("--manifest", type=Path)
    analyze_parser.add_argument("--csv", type=Path, default=Path("data/derived/run_metrics.csv"))
    analyze_parser.add_argument("--mime-csv", type=Path, default=Path("data/derived/mime_metrics.csv"))
    analyze_parser.add_argument("--summary-csv", type=Path, default=Path("data/derived/summary_metrics.csv"))

    page_parser = subparsers.add_parser(
        "analyze-page-metrics",
        help="Analyze manually exported page-metrics JSON files and write CSV outputs.",
    )
    page_parser.add_argument("metrics_root", type=Path)
    page_parser.add_argument("--csv", type=Path, default=Path("data/derived/page_metrics_runs.csv"))
    page_parser.add_argument("--summary-csv", type=Path, default=Path("data/derived/page_metrics_summary.csv"))

    args = parser.parse_args()

    if args.command == "serve":
        serve(args.host, args.port, args.scenario_root.resolve())
        return

    if args.command == "write-manifest":
        config = load_config(args.config.resolve())
        specs = build_manifest(config)
        write_manifest(config.manifest_path, specs)
        print(f"Wrote {len(specs)} run specs to {config.manifest_path}")
        return

    if args.command == "run-manifest":
        run_manifest(
            manifest_path=args.manifest.resolve(),
            post_load_wait_ms=args.post_load_wait_ms,
            trace_enabled=not args.no_trace,
        )
        return

    if args.command == "analyze-har":
        paths = _discover_har_paths(args.har_root.resolve())
        rows = analyze_paths(paths=paths, manifest_path=args.manifest.resolve() if args.manifest else None)
        write_run_csv(args.csv.resolve(), rows)
        write_mime_csv(args.mime_csv.resolve(), rows)
        write_summary_csv(args.summary_csv.resolve(), rows)
        print(f"Analyzed {len(rows)} HAR files.")
        return

    if args.command == "analyze-page-metrics":
        paths = _discover_json_paths(args.metrics_root.resolve())
        rows = analyze_page_metric_paths(paths)
        write_page_metrics_csv(args.csv.resolve(), rows)
        write_page_metrics_summary_csv(args.summary_csv.resolve(), rows)
        print(f"Analyzed {len(rows)} page-metrics JSON files.")
        return


if __name__ == "__main__":
    main()
