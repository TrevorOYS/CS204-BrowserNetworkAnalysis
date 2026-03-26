#!/usr/bin/env python3
import argparse
import csv
import json
import math
import re
from pathlib import Path


def avg_timing(entries, key):
    vals = []
    for e in entries:
        t = e.get("timings", {})
        v = t.get(key)
        if v is None:
            continue
        # HAR uses -1 for unavailable
        if isinstance(v, (int, float)) and v >= 0:
            vals.append(v)
    return (sum(vals) / len(vals)) if vals else None


def load_metrics(path: Path):
    data = json.loads(path.read_text(encoding="utf-8", errors="ignore"))
    log = data.get("log", {})
    entries = log.get("entries", [])
    pages = log.get("pages", [])

    onload = None
    oncontent = None
    if pages:
        pt = pages[0].get("pageTimings", {})
        onload = pt.get("onLoad")
        oncontent = pt.get("onContentLoad")
    
    # Detect Safari HAR (creator name contains "WebKit")
    creator = log.get("creator", {}).get("name", "")
    if "WebKit" in creator and onload and oncontent:
        # Both values are absolute from same reference; delta is the true PLT
        onload = onload - oncontent
        oncontent = None  # no longer meaningful independently

    req_count = len(entries)
    err_count = 0
    total_bytes = 0
    for e in entries:
        status = e.get("response", {}).get("status")
        if isinstance(status, int) and 400 <= status <= 599:
            err_count += 1
        bs = e.get("response", {}).get("bodySize")
        if isinstance(bs, int) and bs > 0:
            total_bytes += bs

    err_rate = (err_count / req_count) if req_count else 0

    dns = avg_timing(entries, "dns")
    connect = avg_timing(entries, "connect")
    ssl = avg_timing(entries, "ssl")
    wait = avg_timing(entries, "wait")  # TTFB proxy
    avg_fetch = None
    fetch_vals = [e.get("time") for e in entries if isinstance(e.get("time"), (int, float)) and e.get("time") >= 0]
    if fetch_vals:
        avg_fetch = sum(fetch_vals) / len(fetch_vals)

    handshake = None
    if connect is not None or ssl is not None:
        handshake = (connect or 0) + (ssl or 0)

    throughput_bps = None
    if onload and onload > 0 and total_bytes > 0:
        throughput_bps = (total_bytes * 8) / (onload / 1000)

    # MIME distribution
    mime_counts = {}
    mime_bytes = {}
    for e in entries:
        mime = e.get("response", {}).get("content", {}).get("mimeType")
        if not mime:
            continue
        top = mime.split(";")[0].strip()
        mime_counts[top] = mime_counts.get(top, 0) + 1
        bs = e.get("response", {}).get("bodySize")
        if isinstance(bs, int) and bs > 0:
            mime_bytes[top] = mime_bytes.get(top, 0) + bs

    return {
        "file": path.name,
        "requests": req_count,
        "errors": err_count,
        "error_rate": err_rate,
        "dns_ms": dns,
        "tcp_tls_ms": handshake,
        "ttfb_ms": wait,
        "plt_ms": onload,
        "oncontent_ms": oncontent,
        "avg_fetch_ms": avg_fetch,
        "total_bytes": total_bytes,
        "throughput_bps": throughput_bps,
        "mime_counts": mime_counts,
        "mime_bytes": mime_bytes,
    }

def main():
    ap = argparse.ArgumentParser(
        description="Extract network metrics from HAR files."
    )
    ap.add_argument("har_dir", help="Directory of HAR files to analyze")
    ap.add_argument(
        "--csv",
        dest="csv_path",
        help="Write results to CSV file",
    )
    ap.add_argument(
        "--mime-csv",
        dest="mime_csv_path",
        help="Write MIME distribution (counts + bytes) to CSV file",
    )
    ap.add_argument(
        "--summary-csv",
        dest="summary_csv_path",
        help="Write grouped summary (mean/stddev) to CSV file",
    )
    args = ap.parse_args()

    har_dir = Path(args.har_dir)
    har_files = sorted(har_dir.glob("*.har"))
    results = [load_metrics(p) for p in har_files]

    # Print to stdout
    for r in results:
        print(r)

    # Create output directory if it doesn't exist
    Path("./output_metrics").mkdir(parents=True, exist_ok=True)

    if args.csv_path:
        fields = [
            "file",
            "requests",
            "errors",
            "error_rate",
            "dns_ms",
            "tcp_tls_ms",
            "ttfb_ms",
            "plt_ms",
            "oncontent_ms",
            "avg_fetch_ms",
            "total_bytes",
            "throughput_bps",
        ]
        with open(f"./output_metrics/{args.csv_path}", "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fields)
            writer.writeheader()
            for r in results:
                writer.writerow({k: r.get(k) for k in fields})

    if args.mime_csv_path:
        # Aggregate MIME counts/bytes per file
        rows = []
        for r in results:
            for mime, count in r["mime_counts"].items():
                rows.append({
                    "file": r["file"],
                    "mime": mime,
                    "count": count,
                    "bytes": r["mime_bytes"].get(mime, 0),
                })
        with open(f"./output_metrics/{args.mime_csv_path}", "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=["file", "mime", "count", "bytes"])
            writer.writeheader()
            writer.writerows(rows)

    if args.summary_csv_path:
        # Group by filename prefix (strip trailing digits and optional underscore)
        groups = {}
        for r in results:
            name = r["file"]
            key = re.sub(r"\d+\.har$", "", name)
            key = re.sub(r"_$", "", key)
            groups.setdefault(key, []).append(r)

        numeric_fields = [
            "requests",
            "errors",
            "error_rate",
            "dns_ms",
            "tcp_tls_ms",
            "ttfb_ms",
            "plt_ms",
            "oncontent_ms",
            "avg_fetch_ms",
            "total_bytes",
            "throughput_bps",
        ]

        summary_rows = []
        for key, items in groups.items():
            row = {"group": key}
            for field in numeric_fields:
                vals = [i.get(field) for i in items if isinstance(i.get(field), (int, float))]
                if not vals:
                    row[field + "_mean"] = None
                    row[field + "_stddev"] = None
                    continue
                mean = sum(vals) / len(vals)
                var = sum((v - mean) ** 2 for v in vals) / (len(vals) if len(vals) > 1 else 1)
                std = math.sqrt(var)
                row[field + "_mean"] = mean
                row[field + "_stddev"] = std
            summary_rows.append(row)

        # Write summary
        fields = ["group"] + [f + "_mean" for f in numeric_fields] + [f + "_stddev" for f in numeric_fields]
        with open(f"./output_metrics/{args.summary_csv_path}", "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fields)
            writer.writeheader()
            writer.writerows(summary_rows)


if __name__ == "__main__":
    main()
