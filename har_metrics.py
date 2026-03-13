#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from browserbench.cli import main as browserbench_main
from browserbench.har_analysis import analyze_paths, write_mime_csv, write_run_csv, write_summary_csv


def legacy_main(argv: list[str]) -> None:
    parser = argparse.ArgumentParser(description="Extract network metrics from HAR files.")
    parser.add_argument("har_dir", help="Directory of HAR files to analyze")
    parser.add_argument("--csv", dest="csv_path", help="Write results to CSV file")
    parser.add_argument("--mime-csv", dest="mime_csv_path", help="Write MIME distribution to CSV file")
    parser.add_argument("--summary-csv", dest="summary_csv_path", help="Write grouped summary to CSV file")
    args = parser.parse_args(argv)

    har_root = Path(args.har_dir).resolve()
    paths = sorted(har_root.glob("*.har"))
    rows = analyze_paths(paths)

    output_dir = Path("./output_metrics")
    output_dir.mkdir(parents=True, exist_ok=True)

    if args.csv_path:
        write_run_csv(output_dir / args.csv_path, rows)
    if args.mime_csv_path:
        write_mime_csv(output_dir / args.mime_csv_path, rows)
    if args.summary_csv_path:
        write_summary_csv(output_dir / args.summary_csv_path, rows)

    for row in rows:
        print(row)


if __name__ == "__main__":
    known_commands = {"serve", "write-manifest", "run-manifest", "analyze-har"}
    argv = sys.argv[1:]
    if argv and argv[0] not in known_commands and not argv[0].startswith("-"):
        legacy_main(argv)
    else:
        browserbench_main()
