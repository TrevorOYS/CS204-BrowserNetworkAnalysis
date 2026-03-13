from __future__ import annotations

from dataclasses import asdict, dataclass
import json
from pathlib import Path

from .config import BenchmarkConfig, BrowserConfig, ScenarioConfig


@dataclass(slots=True)
class RunSpec:
    run_id: str
    browser: str
    scenario: str
    scenario_url: str
    cache_state: str
    network_profile: str
    repeat_index: int
    headless: bool
    channel: str | None
    executable_path: str | None
    output_dir: str
    har_path: str
    perf_path: str
    trace_path: str | None
    notes: str

    def to_record(self) -> dict[str, object]:
        return asdict(self)


def build_run_spec(
    config: BenchmarkConfig,
    browser: BrowserConfig,
    scenario: ScenarioConfig,
    cache_state: str,
    network_profile: str,
    repeat_index: int,
) -> RunSpec:
    run_id = f"{browser.name}-{scenario.name}-{network_profile}-{cache_state}-{repeat_index:03d}"
    run_dir = config.output_root / run_id
    return RunSpec(
        run_id=run_id,
        browser=browser.name,
        scenario=scenario.name,
        scenario_url=f"{config.base_url}{scenario.path}",
        cache_state=cache_state,
        network_profile=network_profile,
        repeat_index=repeat_index,
        headless=browser.headless,
        channel=browser.channel,
        executable_path=browser.executable_path,
        output_dir=str(run_dir),
        har_path=str(run_dir / "network.har"),
        perf_path=str(run_dir / "page_metrics.json"),
        trace_path=str(run_dir / "trace.zip") if config.trace_enabled else None,
        notes="Apply network shaping externally before this run.",
    )


def build_manifest(config: BenchmarkConfig) -> list[RunSpec]:
    specs: list[RunSpec] = []
    for browser in config.browsers:
        for scenario in config.scenarios:
            for network_profile in config.network_profiles:
                for cache_state in config.cache_states:
                    for repeat_index in range(1, config.repetitions + 1):
                        specs.append(
                            build_run_spec(
                                config=config,
                                browser=browser,
                                scenario=scenario,
                                cache_state=cache_state,
                                network_profile=network_profile,
                                repeat_index=repeat_index,
                            )
                        )
    return specs


def write_manifest(path: Path, specs: list[RunSpec]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for spec in specs:
            handle.write(json.dumps(spec.to_record(), sort_keys=True) + "\n")


def load_manifest(path: Path) -> list[dict[str, object]]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]

