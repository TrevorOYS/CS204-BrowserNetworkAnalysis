# Troubleshooting

## Start Here

For the project’s main workflow, you do not need Playwright.

If automation becomes unstable on a device, fall back to:

1. `browserbench serve`
2. manual page load in the target browser
3. export JSON from the page panel
4. `browserbench analyze-page-metrics`

That is the default workflow now.

## The Page Panel Does Not Show Up

Check:

- the page fully loaded
- JavaScript is enabled
- you are using one of the scenario pages under `scenarios/`

If needed, reload once and wait a second or two after the page finishes loading.

## Exported JSON Is Missing Fields

Some metrics are browser-dependent.

It is normal for some browsers to omit:

- LCP
- CLS
- first-contentful-paint

Record missing values as missing. Do not invent replacements.

## HAR Export Differs Across Browsers

That is expected. HAR is supporting evidence, not the only artifact.

Use the exported page-metrics JSON as the main cross-browser dataset.

## Optional Playwright Path

The Playwright backend remains experimental. Use it only when:

- the browser/OS combination is known to work
- the team wants automation for a specific subset of browsers
- you treat manual JSON export as the fallback
