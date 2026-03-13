# NixOS Setup Notes

## Main Point

For this project, NixOS should be treated as:

- a good host for the shared local server
- a good machine for aggregating JSON and HAR artifacts
- not the required automation host for every browser

The main workflow no longer depends on Playwright working across every browser on NixOS.

## Recommended NixOS Workflow

1. Enter a shell and install the base package:

```bash
nix develop
uv pip install -e .
```

2. Start the local server:

```bash
browserbench serve
```

3. Open the scenario page in a target browser.

4. Export page-metrics JSON from the in-browser panel.

5. Save those JSON files under:

```text
data/manual/collected/
```

6. Analyze them:

```bash
browserbench analyze-page-metrics data/manual/collected
```

## Optional Automation Path

Playwright is still available as an experimental backend:

```bash
uv pip install -e .[runner]
```

But the project no longer depends on it, and NixOS should not be the team’s only path for browser automation.

## Browsers

You said you currently have:

- Firefox
- Tor Browser

That is enough to:

- host and validate the shared scenarios
- export page-metrics JSON manually
- analyze the collected results

It is not enough to represent the entire team’s browser matrix. Use teammates with Windows and macOS machines for additional browsers.
