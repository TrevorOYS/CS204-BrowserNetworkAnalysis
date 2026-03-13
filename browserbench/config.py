from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import tomllib


@dataclass(slots=True)
class BrowserConfig:
    name: str
    enabled: bool
    channel: str | None = None
    executable_path: str | None = None
    headless: bool = False


@dataclass(slots=True)
class ScenarioConfig:
    name: str
    path: str


@dataclass(slots=True)
class BenchmarkConfig:
    base_url: str
    output_root: Path
    manifest_path: Path
    post_load_wait_ms: int
    trace_enabled: bool
    repetitions: int
    cache_states: list[str]
    browsers: list[BrowserConfig]
    scenarios: list[ScenarioConfig]
    network_profiles: list[str]


def load_config(path: Path) -> BenchmarkConfig:
    raw = tomllib.loads(path.read_text(encoding="utf-8"))

    benchmark = raw.get("benchmark", {})
    base_url = benchmark.get("base_url", "http://127.0.0.1:8000")
    output_root = Path(benchmark.get("output_root", "data/raw"))
    manifest_path = Path(benchmark.get("manifest_path", "data/manifests/run_manifest.jsonl"))
    post_load_wait_ms = int(benchmark.get("post_load_wait_ms", 1000))
    trace_enabled = bool(benchmark.get("trace_enabled", True))
    repetitions = int(benchmark.get("repetitions", 5))
    cache_states = list(benchmark.get("cache_states", ["cold", "warm"]))
    network_profiles = list(benchmark.get("network_profiles", ["baseline"]))

    browsers = []
    for name, values in raw.get("browsers", {}).items():
        browsers.append(
            BrowserConfig(
                name=name,
                enabled=bool(values.get("enabled", False)),
                channel=values.get("channel"),
                executable_path=values.get("executable_path"),
                headless=bool(values.get("headless", False)),
            )
        )

    scenarios = []
    for name, values in raw.get("scenarios", {}).items():
        scenarios.append(ScenarioConfig(name=name, path=values["path"]))

    if not scenarios:
        raise ValueError("Config must define at least one scenario.")

    enabled_browsers = [browser for browser in browsers if browser.enabled]
    if not enabled_browsers:
        raise ValueError("Config must enable at least one browser.")

    return BenchmarkConfig(
        base_url=base_url.rstrip("/"),
        output_root=output_root,
        manifest_path=manifest_path,
        post_load_wait_ms=post_load_wait_ms,
        trace_enabled=trace_enabled,
        repetitions=repetitions,
        cache_states=cache_states,
        browsers=enabled_browsers,
        scenarios=scenarios,
        network_profiles=network_profiles,
    )

