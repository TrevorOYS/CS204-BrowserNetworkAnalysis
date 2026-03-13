# BrowserBench

BrowserBench is a team-friendly benchmark scaffold for a networking project on browser performance. The repo now centers on a workflow that works across mixed devices:

- one shared local server
- three repeatable page scenarios
- browser-native page metrics exported directly from the page
- optional HAR and waterfall captures as supporting evidence
- optional Playwright automation only where it behaves well

This is designed to support a narrower and more defensible project question:

"Which browser gives the best network performance under controlled conditions?"

## Recommended Scope

Main study:

- Chrome or Chromium
- Firefox
- Brave
- Safari only if one teammate has a Mac

Separate case study:

- Tor Browser

Do not treat Tor as part of the same main ranking. Its design goals are different.

## Core Workflow

1. Start the local benchmark server.
2. Open one of the shared scenarios in a browser.
3. Use the built-in BrowserBench panel on the page to export a JSON artifact for that run.
4. Optionally export HAR or capture waterfall screenshots from that browser's devtools.
5. Store the JSON files in `data/manual/collected/`.
6. Analyze them with `browserbench analyze-page-metrics`.

This keeps the project usable across NixOS, Windows, and macOS even when one automation framework cannot handle every browser cleanly.

## Repository Layout

```text
browserbench/                  Python package and analysis tools
configs/                       Experimental automation configs
data/templates/                Shared CSV template for manual collection
docs/                          Team workflow, methodology, setup, troubleshooting
scenarios/                     Shared benchmark pages
JSIAR-A-25-04250.pdf           Reference paper
har_metrics.py                 Backward-compatible HAR wrapper
```

## Quick Start

Install the base package:

```bash
uv pip install -e .
```

If you want the experimental Playwright backend too:

```bash
uv pip install -e .[runner]
```

Start the local server:

```bash
browserbench serve --host 127.0.0.1 --port 8000
```

Open:

- `http://127.0.0.1:8000/`
- `http://127.0.0.1:8000/minimal/index.html`
- `http://127.0.0.1:8000/moderate/index.html`
- `http://127.0.0.1:8000/heavy/index.html`

When the page settles, fill out the BrowserBench panel and click `Download JSON`.

Suggested storage location:

```text
data/manual/collected/
```

Analyze the exported JSON files:

```bash
browserbench analyze-page-metrics data/manual/collected
```

Optional HAR analysis:

```bash
browserbench analyze-har path/to/har/files
```

## Main Commands

```bash
browserbench serve
browserbench analyze-page-metrics <metrics_root>
browserbench analyze-har <har_root>
```

Experimental only:

```bash
browserbench write-manifest <config.toml>
browserbench run-manifest <manifest.jsonl>
```

## What The Page JSON Captures

The built-in metrics panel exports:

- tester-entered metadata
- browser label
- device and OS labels
- scenario
- network profile
- cache state
- TTFB
- DOMContentLoaded
- page load time
- first paint
- first contentful paint
- LCP where available
- CLS where available
- resource count
- transfer size summary

This is the primary cross-browser artifact for the project.

## Recommended Team Workflow

Use one shared testing protocol for all teammates.

- one person owns the local server and scenario pages
- each teammate runs the browsers available on their own device
- everyone exports page JSON using the same protocol
- HAR and waterfall captures are supporting evidence, not the only data source
- one person aggregates results and writes charts

Start with:

- `minimal`, `moderate`, `heavy`
- `baseline`, `latency100ms`, `bandwidth512kbps`
- `cold` and `warm`
- at least `10` runs per condition if time allows

## NixOS

NixOS is still useful for:

- hosting the shared local server
- serving scenarios
- aggregating JSON and HAR artifacts
- writing charts and reports

But the main workflow no longer depends on Playwright working across every browser on NixOS.

See:

- [team-protocol.md](/home/Hephaestus/Personal/001_Code/CS204-BrowserNetworkAnalysis/docs/team-protocol.md)
- [methodology.md](/home/Hephaestus/Personal/001_Code/CS204-BrowserNetworkAnalysis/docs/methodology.md)
- [repo-structure.md](/home/Hephaestus/Personal/001_Code/CS204-BrowserNetworkAnalysis/docs/repo-structure.md)
- [setup-nixos.md](/home/Hephaestus/Personal/001_Code/CS204-BrowserNetworkAnalysis/docs/setup-nixos.md)
- [troubleshooting.md](/home/Hephaestus/Personal/001_Code/CS204-BrowserNetworkAnalysis/docs/troubleshooting.md)
