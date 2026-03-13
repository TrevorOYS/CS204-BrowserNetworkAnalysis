# Methodology

This repo uses the ideas from `JSIAR-A-25-04250.pdf`, but adapts them for a mixed-device student team. The main workflow is now browser-native page metrics plus optional HAR exports, not one universal automation framework.

## Main Benchmark Matrix

Compare:

- browser
- scenario
- network profile
- cache state
- repetition index

Recommended first matrix:

- browsers: `firefox`, `chrome` or `chromium`, `brave`
- scenarios: `minimal`, `moderate`, `heavy`
- network profiles: `baseline`, `100 ms latency`, `512 kbps bandwidth`
- cache states: `cold`, `warm`
- repetitions: `10` minimum, `20-30` if time allows

## Why the Repo Uses Page Metrics as the Primary Artifact

The team is using mixed operating systems and mixed browsers. Browser-native Performance APIs are the most portable common layer. Every scenario page now includes an export panel that writes a JSON artifact with:

- metadata entered by the tester
- navigation timing
- paint metrics
- LCP and CLS where available
- resource counts and transfer-size summary

This is the main cross-browser artifact.

## Optional HAR Path

HAR is still useful, but as supporting evidence rather than the only source of truth.

Use HAR for:

- request count
- status codes and error rate
- DNS timing
- TCP connect timing
- TLS timing
- request wait timing
- MIME mix
- protocol mix
- waterfall evidence

## Metrics to Use in the Report

Use page-metrics JSON for:

- TTFB
- DOMContentLoaded
- page load time
- first paint
- first contentful paint
- LCP
- CLS
- resource count
- transfer size

## Known Constraints

- HAR does not fully capture speculative prefetch, service worker internals, or all browser-private telemetry.
- Playwright WebKit is not actual Safari.
- Playwright Firefox is not stock Firefox release.
- Tor Browser should be treated as a separate case study.
- Manual collection introduces some operator variability, which must be acknowledged in the report.

## Scenario Design

The scenarios in `scenarios/` are local pages that request generated CSS, JS, JSON, and SVG assets from the same server. Each page includes a metrics panel that lets a tester export a structured JSON file for that run.

The scenario size classes are approximate:

- `minimal`: target under `500 KB`
- `moderate`: target around `1.5 MB`
- `heavy`: target `5 MB+`

## Traffic Shaping

Traffic shaping remains external to the repo. Use the same method for all browsers and document it clearly in the report.
