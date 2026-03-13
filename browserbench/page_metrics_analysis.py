from __future__ import annotations

import csv
import json
import math
from pathlib import Path
from statistics import median
from typing import Any


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


def _coerce_number(value: Any) -> float | None:
    if isinstance(value, NUMERIC):
        return float(value)
    return None


def _infer_browser_label(browser: str | None, user_agent: str | None) -> str | None:
    if browser:
        return str(browser)
    ua = (user_agent or "").lower()
    if "tor browser" in ua:
        return "tor"
    if "brave" in ua:
        return "brave"
    if "firefox" in ua:
        return "firefox"
    if "edg/" in ua:
        return "edge"
    if "chrome" in ua and "chromium" not in ua:
        return "chrome"
    if "chromium" in ua:
        return "chromium"
    if "safari" in ua and "chrome" not in ua:
        return "safari"
    return None


def _paint_value(paints: dict[str, Any], key: str) -> float | None:
    value = paints.get(key)
    if isinstance(value, NUMERIC):
        return float(value)
    return None


def load_page_metrics(path: Path) -> dict[str, object]:
    data = json.loads(path.read_text(encoding="utf-8"))
    metadata = data.get("metadata", {})
    summary = data.get("summary", {})
    paints = data.get("paints", {})
    navigation = data.get("navigation", {})
    resource_summary = data.get("resource_summary", {})

    browser = metadata.get("browser_label") or data.get("browser")
    user_agent = data.get("user_agent")

    return {
        "file": path.name,
        "page_metrics_path": str(path),
        "tester": metadata.get("tester"),
        "browser_label": _infer_browser_label(browser, user_agent),
        "device_label": metadata.get("device_label"),
        "os_label": metadata.get("os_label"),
        "scenario": metadata.get("scenario") or data.get("scenario"),
        "network_profile": metadata.get("network_profile") or data.get("network_profile"),
        "cache_state": metadata.get("cache_state") or data.get("cache_state"),
        "run_number": metadata.get("run_number") or data.get("repeat_index"),
        "notes": metadata.get("notes"),
        "page_url": data.get("location"),
        "page_title": data.get("title"),
        "user_agent": user_agent,
        "page_load_ms": _coerce_number(summary.get("page_load_ms")),
        "dom_content_loaded_ms": _coerce_number(summary.get("dom_content_loaded_ms")),
        "ttfb_ms": _coerce_number(summary.get("ttfb_ms")),
        "first_paint_ms": _paint_value(paints, "first-paint"),
        "first_contentful_paint_ms": _paint_value(paints, "first-contentful-paint"),
        "lcp_ms": _coerce_number(summary.get("lcp_ms") or data.get("lcp_ms")),
        "cls": _coerce_number(summary.get("cls") or data.get("cls")),
        "resource_count": int(resource_summary.get("resource_count", data.get("resource_count", 0)) or 0),
        "transfer_size_bytes": int(resource_summary.get("transfer_size_bytes", 0) or 0),
        "encoded_body_bytes": int(resource_summary.get("encoded_body_bytes", 0) or 0),
        "decoded_body_bytes": int(resource_summary.get("decoded_body_bytes", 0) or 0),
        "navigation_type": navigation.get("type"),
        "redirect_count": navigation.get("redirectCount"),
    }


def analyze_paths(paths: list[Path]) -> list[dict[str, object]]:
    return [load_page_metrics(path) for path in paths]


def write_run_csv(path: Path, rows: list[dict[str, object]]) -> None:
    fieldnames = [
        "file",
        "tester",
        "browser_label",
        "device_label",
        "os_label",
        "scenario",
        "network_profile",
        "cache_state",
        "run_number",
        "notes",
        "page_url",
        "page_title",
        "page_load_ms",
        "dom_content_loaded_ms",
        "ttfb_ms",
        "first_paint_ms",
        "first_contentful_paint_ms",
        "lcp_ms",
        "cls",
        "resource_count",
        "transfer_size_bytes",
        "encoded_body_bytes",
        "decoded_body_bytes",
        "navigation_type",
        "redirect_count",
        "page_metrics_path",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({key: row.get(key) for key in fieldnames})


def write_summary_csv(path: Path, rows: list[dict[str, object]]) -> None:
    group_fields = ["browser_label", "scenario", "network_profile", "cache_state"]
    metrics = [
        "page_load_ms",
        "dom_content_loaded_ms",
        "ttfb_ms",
        "first_paint_ms",
        "first_contentful_paint_ms",
        "lcp_ms",
        "cls",
        "resource_count",
        "transfer_size_bytes",
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

    fieldnames = ["browser_label", "scenario", "network_profile", "cache_state", "runs"]
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
