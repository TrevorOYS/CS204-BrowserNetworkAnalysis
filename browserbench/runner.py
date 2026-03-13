from __future__ import annotations

import json
import os
import shutil
from pathlib import Path
from typing import Any


PROBE_SCRIPT = r"""
(() => {
  window.__browserbench = {
    cls: 0,
    lcp: null,
    lcpSize: null,
  };

  try {
    new PerformanceObserver((list) => {
      for (const entry of list.getEntries()) {
        if (!entry.hadRecentInput) {
          window.__browserbench.cls += entry.value;
        }
      }
    }).observe({ type: "layout-shift", buffered: true });
  } catch (error) {
    window.__browserbench.clsObserverError = String(error);
  }

  try {
    new PerformanceObserver((list) => {
      const entries = list.getEntries();
      const entry = entries[entries.length - 1];
      if (entry) {
        window.__browserbench.lcp = entry.startTime;
        window.__browserbench.lcpSize = entry.size || null;
      }
    }).observe({ type: "largest-contentful-paint", buffered: true });
  } catch (error) {
    window.__browserbench.lcpObserverError = String(error);
  }
})();
"""


EXTRACT_SCRIPT = r"""
() => {
  const navigation = performance.getEntriesByType("navigation")[0];
  const paints = performance.getEntriesByType("paint").map((entry) => entry.toJSON());
  const resources = performance.getEntriesByType("resource").map((entry) => entry.toJSON());
  return {
    location: window.location.href,
    title: document.title,
    user_agent: navigator.userAgent,
    navigation: navigation ? navigation.toJSON() : null,
    paints,
    resource_count: resources.length,
    resource_samples: resources.slice(0, 10),
    lcp_ms: window.__browserbench?.lcp ?? null,
    lcp_size: window.__browserbench?.lcpSize ?? null,
    cls: window.__browserbench?.cls ?? null,
    timestamp_ms: performance.now(),
  };
}
"""


def _load_playwright():
    try:
        from playwright.sync_api import sync_playwright
    except ImportError as exc:  # pragma: no cover - import error path
        message = str(exc)
        if "libstdc++.so.6" in message:
            raise RuntimeError(
                "Playwright's Python dependencies could not load libstdc++.so.6. "
                "On NixOS, export LD_LIBRARY_PATH to the GCC runtime lib directory or use the repo's Nix shell. "
                "Example: export LD_LIBRARY_PATH=\"$(dirname $(gcc -print-file-name=libstdc++.so.6)):${LD_LIBRARY_PATH:-}\""
            ) from exc
        raise RuntimeError(
            "Playwright is not installed. Install the optional runner dependency "
            "with `uv pip install -e .[runner]` or `pip install -e .[runner]`."
        ) from exc
    return sync_playwright


def _on_nixos() -> bool:
    return Path("/etc/NIXOS").exists() or Path("/run/current-system").exists()


def _preflight_runtime() -> None:
    if _on_nixos() and not os.environ.get("PLAYWRIGHT_NODEJS_PATH"):
        raise RuntimeError(
            "NixOS detected but PLAYWRIGHT_NODEJS_PATH is not set. "
            "Playwright's bundled Node binary will usually fail on NixOS. "
            "Use your system node instead, for example: "
            "export PLAYWRIGHT_NODEJS_PATH=\"$(which node)\""
        )


def _launch_browser(playwright: Any, spec: dict[str, Any]):
    browser_name = spec["browser"]
    launch_kwargs: dict[str, Any] = {
        "headless": bool(spec.get("headless", False)),
    }

    executable_path = spec.get("executable_path")
    channel = spec.get("channel")

    if browser_name == "chromium":
        if channel:
            launch_kwargs["channel"] = channel
        if executable_path:
            launch_kwargs["executable_path"] = executable_path
        return playwright.chromium.launch(**launch_kwargs)

    if browser_name == "chrome":
        launch_kwargs["channel"] = channel or "chrome"
        if executable_path:
            launch_kwargs["executable_path"] = executable_path
        return playwright.chromium.launch(**launch_kwargs)

    if browser_name == "firefox":
        using_system_firefox = False
        if _on_nixos() and not executable_path:
            system_firefox = shutil.which("firefox")
            if system_firefox:
                executable_path = system_firefox
                using_system_firefox = True
        elif executable_path and "/.cache/ms-playwright/" not in executable_path:
            using_system_firefox = True

        # On NixOS, a shell-wide LD_LIBRARY_PATH is useful for Playwright's Node
        # and Python wheels, but it can break system Firefox by overriding the
        # exact NSS/GTK stack Firefox was built against.
        if _on_nixos() and using_system_firefox:
            browser_env = dict(os.environ)
            browser_env["LD_LIBRARY_PATH"] = ""
            browser_env["LD_PRELOAD"] = ""
            browser_env["NIX_LD"] = ""
            browser_env["NIX_LD_LIBRARY_PATH"] = ""
            launch_kwargs["env"] = browser_env

        if channel or executable_path:
            launch_kwargs.update(
                {k: v for k, v in {"channel": channel, "executable_path": executable_path}.items() if v}
            )
        return playwright.firefox.launch(**launch_kwargs)

    if browser_name == "webkit":
        return playwright.webkit.launch(**launch_kwargs)

    if browser_name == "brave":
        if not executable_path:
            raise RuntimeError(
                "Brave requires `executable_path` in the manifest or config. "
                "Playwright does not provide an official Brave channel."
            )
        launch_kwargs["executable_path"] = executable_path
        return playwright.chromium.launch(**launch_kwargs)

    if browser_name == "tor":
        raise RuntimeError(
            "Tor Browser is not supported by the shared Playwright harness. "
            "Keep Tor as a separate study."
        )

    raise RuntimeError(f"Unsupported browser '{browser_name}'.")


def run_manifest(manifest_path: Path, post_load_wait_ms: int = 1000, trace_enabled: bool = True) -> None:
    _preflight_runtime()
    rows = [
        json.loads(line)
        for line in manifest_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    sync_playwright = _load_playwright()

    with sync_playwright() as playwright:
        for spec in rows:
            run_one(playwright=playwright, spec=spec, post_load_wait_ms=post_load_wait_ms, trace_enabled=trace_enabled)


def run_one(playwright: Any, spec: dict[str, Any], post_load_wait_ms: int, trace_enabled: bool) -> None:
    output_dir = Path(spec["output_dir"])
    output_dir.mkdir(parents=True, exist_ok=True)

    browser = _launch_browser(playwright, spec)
    context = browser.new_context(record_har_path=spec["har_path"])
    page = context.new_page()
    page.add_init_script(PROBE_SCRIPT)

    if trace_enabled and spec.get("trace_path"):
        context.tracing.start(screenshots=False, snapshots=False)

    try:
        target_url = spec["scenario_url"]
        if spec["cache_state"] == "warm":
            page.goto(target_url, wait_until="load")
            page.wait_for_timeout(post_load_wait_ms)
            page.goto(target_url, wait_until="load")
        else:
            page.goto(target_url, wait_until="load")

        page.wait_for_timeout(post_load_wait_ms)
        perf_metrics = page.evaluate(EXTRACT_SCRIPT)
        perf_metrics["run_id"] = spec["run_id"]
        perf_metrics["browser"] = spec["browser"]
        perf_metrics["scenario"] = spec["scenario"]
        perf_metrics["cache_state"] = spec["cache_state"]
        perf_metrics["network_profile"] = spec["network_profile"]

        Path(spec["perf_path"]).write_text(
            json.dumps(perf_metrics, indent=2, sort_keys=True),
            encoding="utf-8",
        )
    finally:
        if trace_enabled and spec.get("trace_path"):
            context.tracing.stop(path=spec["trace_path"])
        context.close()
        browser.close()
