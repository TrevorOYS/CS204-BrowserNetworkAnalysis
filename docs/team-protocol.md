# Team Testing Protocol

## Project Question

Use this framing:

"Which browser gives the best network performance under controlled conditions?"

Do not treat "best" as one universal score. Rank browsers by category.

## Main Study Scope

Recommended primary browsers:

- Chrome or Chromium
- Firefox
- Brave
- Safari only if one teammate has a Mac

Recommended separate case study:

- Tor Browser

## Shared Variables

Independent variables:

- browser
- scenario: `minimal`, `moderate`, `heavy`
- network profile: `baseline`, `latency100ms`, `bandwidth512kbps`
- cache state: `cold`, `warm`

Dependent variables:

- TTFB
- DOMContentLoaded
- page load time
- first paint
- first contentful paint
- LCP if available
- CLS if available
- resource count
- transfer size

## Per-Run Procedure

1. Start the local server.
2. Open the assigned browser.
3. Open the assigned scenario URL.
4. Wait until the built-in BrowserBench panel appears and the summary is populated.
5. Fill in the metadata fields in the panel.
6. Download the JSON artifact.
7. Export a HAR file or take a waterfall screenshot if that browser supports it.
8. Record the artifact name in `data/templates/manual_run_log.csv` or your shared spreadsheet.

For `cold` cache runs:

- clear browser cache before each run
- close the tab and reopen it if needed

For `warm` cache runs:

- load once
- reload the same page without clearing cache
- export the second run

## Minimum Run Count

Use at least:

- 5 runs per condition for a pilot
- 10 runs per condition for the final report

If time allows, push to 20 or 30 for the final dataset.

## Team Split

Suggested split for five people:

- Person 1: local server and scenario ownership
- Person 2: Chrome or Chromium runs
- Person 3: Firefox runs
- Person 4: Brave or Safari runs
- Person 5: data cleaning, charts, and report integration

If a Mac is available, give Safari to the Mac user. If not, state Safari is out of scope.

## Final Analysis Rule

The primary cross-browser artifact is the exported page-metrics JSON from the page itself. HAR and waterfall data are supporting artifacts, not the only source of truth.
