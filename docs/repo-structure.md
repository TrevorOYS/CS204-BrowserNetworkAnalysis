# Repo Structure

This repo is now organized around a manual or semi-manual team workflow.

## Core Paths

- `scenarios/`
  - local benchmark pages
  - each page includes an in-browser metrics capture panel

- `data/templates/manual_run_log.csv`
  - shared sheet structure for the team

- `browserbench/page_metrics_analysis.py`
  - analysis for exported page-metrics JSON

- `browserbench/har_analysis.py`
  - optional HAR analysis if a browser can export HAR

- `browserbench/runner.py`
  - experimental Playwright backend
  - not the main workflow

## Recommended Artifact Layout

- `data/manual/collected/`
  - downloaded page-metrics JSON files from browsers

- `data/raw/`
  - optional Playwright artifacts

- `data/derived/`
  - aggregated CSV outputs

## Main Commands

- `browserbench serve`
- `browserbench analyze-page-metrics <dir>`
- `browserbench analyze-har <dir>`

Use `run-manifest` only if you intentionally want to experiment with Playwright on a platform where it behaves well.
