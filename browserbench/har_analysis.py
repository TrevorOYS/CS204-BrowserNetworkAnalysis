from __future__ import annotations

import csv
import json
import math
from pathlib import Path
from statistics import median
from urllib.parse import urlparse


NUMERIC = (int, float)


def percentile(values: list[float], rank: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0]
    position = (len(ordered) - 1) * rank
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return ordered[lower]
    weight = position - lower
    return ordered[lower] * (1 - weight) + ordered[upper] * weight


def _valid_timing(entry: dict, key: str) -> float | None:
    value = entry.get("timings", {}).get(key)
    if isinstance(value, NUMERIC) and value >= 0:
        return float(value)
    return None


def _numeric_stats(values: list[float], prefix: str) -> dict[str, float | None]:
    if not values:
        return {
            f"{prefix}_mean_ms": None,
            f"{prefix}_median_ms": None,
            f"{prefix}_p95_ms": None,
        }
    return {
        f"{prefix}_mean_ms": sum(values) / len(values),
        f"{prefix}_median_ms": median(values),
        f"{prefix}_p95_ms": percentile(values, 0.95),
    }


def _detect_cache_hit(entry: dict) -> bool:
    response = entry.get("response", {})
    if response.get("status") == 304:
        return True
    if entry.get("_servedFromCache") is True:
        return True
    if response.get("_fromCache") is True:
        return True
    cache = entry.get("cache", {})
    if cache.get("beforeRequest") or cache.get("afterRequest"):
        return True
    return False


def _find_primary_document(entries: list[dict]) -> dict | None:
    if not entries:
        return None
    html_entries = [
        entry
        for entry in entries
        if str(entry.get("response", {}).get("content", {}).get("mimeType", "")).startswith("text/html")
    ]
    candidates = html_entries or entries
    return min(candidates, key=lambda item: item.get("startedDateTime", ""))


def _page_host(entries: list[dict]) -> str | None:
    doc = _find_primary_document(entries)
    if not doc:
        return None
    return urlparse(doc.get("request", {}).get("url", "")).hostname


def _select_page(log: dict) -> tuple[dict | None, list[dict]]:
    pages = log.get("pages", [])
    entries = log.get("entries", [])
    if not pages:
        return None, entries
    page = pages[-1]
    pageref = page.get("id")
    selected = [entry for entry in entries if entry.get("pageref") == pageref]
    return page, selected or entries


def load_metrics(path: Path) -> dict[str, object]:
    data = json.loads(path.read_text(encoding="utf-8", errors="ignore"))
    log = data.get("log", {})
    page, entries = _select_page(log)

    onload = None
    oncontent = None
    if page:
        page_timings = page.get("pageTimings", {})
        onload = page_timings.get("onLoad")
        oncontent = page_timings.get("onContentLoad")

    req_count = len(entries)
    err_count = 0
    total_bytes = 0
    cached = 0
    third_party = 0
    first_party = 0
    status_counts: dict[str, int] = {}
    protocol_counts: dict[str, int] = {}
    mime_counts: dict[str, int] = {}
    mime_bytes: dict[str, int] = {}
    host = _page_host(entries)

    for entry in entries:
        response = entry.get("response", {})
        status = response.get("status")
        if isinstance(status, int) and 400 <= status <= 599:
            err_count += 1
        if isinstance(status, int):
            status_key = f"{status // 100}xx"
            status_counts[status_key] = status_counts.get(status_key, 0) + 1

        protocol = response.get("httpVersion")
        if protocol:
            protocol_counts[str(protocol)] = protocol_counts.get(str(protocol), 0) + 1

        body_size = response.get("bodySize")
        if isinstance(body_size, int) and body_size > 0:
            total_bytes += body_size

        if _detect_cache_hit(entry):
            cached += 1

        mime = response.get("content", {}).get("mimeType")
        if mime:
            top = mime.split(";")[0].strip()
            mime_counts[top] = mime_counts.get(top, 0) + 1
            if isinstance(body_size, int) and body_size > 0:
                mime_bytes[top] = mime_bytes.get(top, 0) + body_size

        request_host = urlparse(entry.get("request", {}).get("url", "")).hostname
        if host and request_host:
            if request_host == host:
                first_party += 1
            else:
                third_party += 1

    err_rate = (err_count / req_count) if req_count else 0.0
    cache_hit_ratio = (cached / req_count) if req_count else 0.0

    dns_values = [value for entry in entries if (value := _valid_timing(entry, "dns")) is not None]
    connect_values = [value for entry in entries if (value := _valid_timing(entry, "connect")) is not None]
    ssl_values = [value for entry in entries if (value := _valid_timing(entry, "ssl")) is not None]
    wait_values = [value for entry in entries if (value := _valid_timing(entry, "wait")) is not None]
    fetch_values = [
        float(entry["time"])
        for entry in entries
        if isinstance(entry.get("time"), NUMERIC) and entry["time"] >= 0
    ]

    primary_document = _find_primary_document(entries)
    primary_ttfb = _valid_timing(primary_document, "wait") if primary_document else None
    primary_url = primary_document.get("request", {}).get("url") if primary_document else None

    throughput_bps = None
    if isinstance(onload, NUMERIC) and onload > 0 and total_bytes > 0:
        throughput_bps = (total_bytes * 8) / (float(onload) / 1000)

    metrics: dict[str, object] = {
        "file": path.name,
        "har_path": str(path),
        "page_title": page.get("title") if page else None,
        "page_id": page.get("id") if page else None,
        "primary_document_url": primary_url,
        "requests": req_count,
        "errors": err_count,
        "error_rate": err_rate,
        "cache_hit_count": cached,
        "cache_hit_ratio": cache_hit_ratio,
        "first_party_requests": first_party,
        "third_party_requests": third_party,
        "primary_doc_ttfb_ms": primary_ttfb,
        "plt_ms": onload,
        "oncontent_ms": oncontent,
        "avg_fetch_ms": (sum(fetch_values) / len(fetch_values)) if fetch_values else None,
        "total_bytes": total_bytes,
        "effective_page_throughput_bps": throughput_bps,
        "status_counts": status_counts,
        "protocol_counts": protocol_counts,
        "mime_counts": mime_counts,
        "mime_bytes": mime_bytes,
    }

    metrics.update(_numeric_stats(dns_values, "dns"))
    metrics.update(_numeric_stats(connect_values, "connect"))
    metrics.update(_numeric_stats(ssl_values, "ssl"))
    metrics.update(_numeric_stats(wait_values, "request_wait"))
    return metrics


def load_manifest_index(path: Path | None) -> dict[str, dict[str, object]]:
    if not path:
        return {}
    index: dict[str, dict[str, object]] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        record = json.loads(line)
        har_path = Path(record["har_path"]).resolve()
        index[str(har_path)] = record
    return index


def analyze_paths(paths: list[Path], manifest_path: Path | None = None) -> list[dict[str, object]]:
    manifest_index = load_manifest_index(manifest_path)
    rows = []
    for path in paths:
        metrics = load_metrics(path)
        manifest_row = manifest_index.get(str(path.resolve()))
        if manifest_row:
            for field in ("run_id", "browser", "scenario", "cache_state", "network_profile", "repeat_index"):
                metrics[field] = manifest_row.get(field)
        rows.append(metrics)
    return rows


def write_run_csv(path: Path, rows: list[dict[str, object]]) -> None:
    fieldnames = [
        "run_id",
        "browser",
        "scenario",
        "cache_state",
        "network_profile",
        "repeat_index",
        "file",
        "requests",
        "errors",
        "error_rate",
        "cache_hit_count",
        "cache_hit_ratio",
        "first_party_requests",
        "third_party_requests",
        "primary_doc_ttfb_ms",
        "dns_mean_ms",
        "dns_median_ms",
        "dns_p95_ms",
        "connect_mean_ms",
        "connect_median_ms",
        "connect_p95_ms",
        "ssl_mean_ms",
        "ssl_median_ms",
        "ssl_p95_ms",
        "request_wait_mean_ms",
        "request_wait_median_ms",
        "request_wait_p95_ms",
        "plt_ms",
        "oncontent_ms",
        "avg_fetch_ms",
        "total_bytes",
        "effective_page_throughput_bps",
        "har_path",
        "primary_document_url",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({key: row.get(key) for key in fieldnames})


def write_mime_csv(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["run_id", "browser", "scenario", "cache_state", "network_profile", "file", "mime", "count", "bytes"],
        )
        writer.writeheader()
        for row in rows:
            mime_counts = row.get("mime_counts", {})
            mime_bytes = row.get("mime_bytes", {})
            for mime, count in mime_counts.items():
                writer.writerow(
                    {
                        "run_id": row.get("run_id"),
                        "browser": row.get("browser"),
                        "scenario": row.get("scenario"),
                        "cache_state": row.get("cache_state"),
                        "network_profile": row.get("network_profile"),
                        "file": row.get("file"),
                        "mime": mime,
                        "count": count,
                        "bytes": mime_bytes.get(mime, 0),
                    }
                )


def write_summary_csv(path: Path, rows: list[dict[str, object]]) -> None:
    group_fields = ["browser", "scenario", "cache_state", "network_profile"]
    metrics = [
        "requests",
        "errors",
        "error_rate",
        "cache_hit_ratio",
        "primary_doc_ttfb_ms",
        "dns_mean_ms",
        "connect_mean_ms",
        "ssl_mean_ms",
        "request_wait_mean_ms",
        "plt_ms",
        "oncontent_ms",
        "avg_fetch_ms",
        "total_bytes",
        "effective_page_throughput_bps",
    ]

    grouped: dict[tuple[object, ...], list[dict[str, object]]] = {}
    for row in rows:
        key = tuple(row.get(field) for field in group_fields)
        grouped.setdefault(key, []).append(row)

    summary_rows = []
    for key, bucket in grouped.items():
        summary: dict[str, object] = {field: value for field, value in zip(group_fields, key)}
        summary["runs"] = len(bucket)
        for metric in metrics:
            values = [float(item[metric]) for item in bucket if isinstance(item.get(metric), NUMERIC)]
            if values:
                mean = sum(values) / len(values)
                variance = sum((value - mean) ** 2 for value in values) / (len(values) if len(values) > 1 else 1)
                summary[f"{metric}_mean"] = mean
                summary[f"{metric}_median"] = median(values)
                summary[f"{metric}_stddev"] = math.sqrt(variance)
                summary[f"{metric}_p95"] = percentile(values, 0.95)
            else:
                summary[f"{metric}_mean"] = None
                summary[f"{metric}_median"] = None
                summary[f"{metric}_stddev"] = None
                summary[f"{metric}_p95"] = None
        summary_rows.append(summary)

    fieldnames = ["browser", "scenario", "cache_state", "network_profile", "runs"]
    for metric in metrics:
        fieldnames.extend(
            [
                f"{metric}_mean",
                f"{metric}_median",
                f"{metric}_stddev",
                f"{metric}_p95",
            ]
        )

    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(summary_rows)

