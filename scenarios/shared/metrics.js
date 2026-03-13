(function () {
  const state = {
    cls: 0,
    lcp: null,
    lcpSize: null,
    paints: {},
  };

  function observeMetrics() {
    try {
      new PerformanceObserver((list) => {
        for (const entry of list.getEntries()) {
          if (!entry.hadRecentInput) {
            state.cls += entry.value;
          }
        }
      }).observe({ type: "layout-shift", buffered: true });
    } catch (error) {
      state.clsObserverError = String(error);
    }

    try {
      new PerformanceObserver((list) => {
        const entries = list.getEntries();
        const entry = entries[entries.length - 1];
        if (entry) {
          state.lcp = entry.startTime;
          state.lcpSize = entry.size || null;
        }
      }).observe({ type: "largest-contentful-paint", buffered: true });
    } catch (error) {
      state.lcpObserverError = String(error);
    }
  }

  function currentScenario() {
    return document.body.getAttribute("data-scenario") || "unknown";
  }

  function readMetadataForm() {
    const panel = document.getElementById("browserbench-panel");
    const query = (name) => panel.querySelector(`[name="${name}"]`);
    return {
      tester: query("tester").value.trim(),
      browser_label: query("browser_label").value.trim(),
      device_label: query("device_label").value.trim(),
      os_label: query("os_label").value.trim(),
      network_profile: query("network_profile").value.trim(),
      cache_state: query("cache_state").value.trim(),
      run_number: query("run_number").value.trim(),
      notes: query("notes").value.trim(),
      scenario: currentScenario(),
    };
  }

  function collectPayload() {
    const nav = performance.getEntriesByType("navigation")[0];
    const paintEntries = performance.getEntriesByType("paint");
    const resources = performance.getEntriesByType("resource");

    state.paints = {};
    for (const entry of paintEntries) {
      state.paints[entry.name] = entry.startTime;
    }

    const transferSize = resources.reduce((sum, entry) => sum + (entry.transferSize || 0), 0);
    const encodedBodySize = resources.reduce((sum, entry) => sum + (entry.encodedBodySize || 0), 0);
    const decodedBodySize = resources.reduce((sum, entry) => sum + (entry.decodedBodySize || 0), 0);

    return {
      exported_at_iso: new Date().toISOString(),
      scenario: currentScenario(),
      location: window.location.href,
      title: document.title,
      user_agent: navigator.userAgent,
      metadata: readMetadataForm(),
      summary: {
        ttfb_ms: nav ? nav.responseStart - nav.requestStart : null,
        dom_content_loaded_ms: nav ? nav.domContentLoadedEventEnd : null,
        page_load_ms: nav ? nav.loadEventEnd : null,
        lcp_ms: state.lcp,
        cls: state.cls,
      },
      paints: state.paints,
      resource_summary: {
        resource_count: resources.length,
        transfer_size_bytes: transferSize,
        encoded_body_bytes: encodedBodySize,
        decoded_body_bytes: decodedBodySize,
      },
      navigation: nav ? nav.toJSON() : null,
      resource_samples: resources.slice(0, 10).map((entry) => entry.toJSON()),
      observer_notes: {
        cls_error: state.clsObserverError || null,
        lcp_error: state.lcpObserverError || null,
      },
    };
  }

  function formatMs(value) {
    if (typeof value !== "number" || !isFinite(value)) {
      return "n/a";
    }
    return `${value.toFixed(1)} ms`;
  }

  function formatBytes(value) {
    if (typeof value !== "number" || !isFinite(value)) {
      return "n/a";
    }
    if (value < 1024) {
      return `${value} B`;
    }
    if (value < 1024 * 1024) {
      return `${(value / 1024).toFixed(1)} KB`;
    }
    return `${(value / (1024 * 1024)).toFixed(2)} MB`;
  }

  function formatNumber(value, decimals) {
    if (typeof value !== "number" || !isFinite(value)) {
      return "n/a";
    }
    return value.toFixed(decimals);
  }

  function renderSummary(payload) {
    const target = document.getElementById("browserbench-summary");
    const summary = payload.summary;
    const resource = payload.resource_summary;
    const rows = [
      ["Scenario", payload.scenario],
      ["TTFB", formatMs(summary.ttfb_ms)],
      ["DOMContentLoaded", formatMs(summary.dom_content_loaded_ms)],
      ["Load", formatMs(summary.page_load_ms)],
      ["First Paint", formatMs(payload.paints["first-paint"])],
      ["FCP", formatMs(payload.paints["first-contentful-paint"])],
      ["LCP", formatMs(summary.lcp_ms)],
      ["CLS", formatNumber(summary.cls, 4)],
      ["Resources", resource.resource_count],
      ["Transfer Size", formatBytes(resource.transfer_size_bytes)],
    ];
    target.innerHTML = rows
      .map(([label, value]) => `<div class="bb-row"><span>${label}</span><strong>${value}</strong></div>`)
      .join("");
  }

  function payloadFilename(payload) {
    const safe = (value) => (value || "unknown").toString().trim().replace(/[^a-zA-Z0-9._-]+/g, "_");
    const meta = payload.metadata;
    return [
      safe(meta.browser_label),
      safe(payload.scenario),
      safe(meta.network_profile),
      safe(meta.cache_state),
      safe(meta.run_number),
      Date.now(),
    ].join("_") + ".json";
  }

  async function copyPayload() {
    const payload = collectPayload();
    renderSummary(payload);
    await navigator.clipboard.writeText(JSON.stringify(payload, null, 2));
  }

  function downloadPayload() {
    const payload = collectPayload();
    renderSummary(payload);
    const blob = new Blob([JSON.stringify(payload, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = payloadFilename(payload);
    document.body.appendChild(anchor);
    anchor.click();
    anchor.remove();
    URL.revokeObjectURL(url);
  }

  function injectPanel() {
    const style = document.createElement("style");
    style.textContent = `
      #browserbench-panel {
        position: fixed;
        right: 1rem;
        bottom: 1rem;
        width: min(28rem, calc(100vw - 2rem));
        z-index: 9999;
        background: rgba(12, 18, 24, 0.94);
        color: #f8f4e8;
        border-radius: 1rem;
        box-shadow: 0 18px 44px rgba(0, 0, 0, 0.28);
        font: 13px/1.35 ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
      }
      #browserbench-panel details { padding: 0.85rem 0.95rem 1rem; }
      #browserbench-panel summary { cursor: pointer; font-weight: 700; }
      #browserbench-panel .bb-grid {
        display: grid;
        grid-template-columns: 1fr 1fr;
        gap: 0.5rem;
        margin-top: 0.8rem;
      }
      #browserbench-panel label { display: grid; gap: 0.2rem; }
      #browserbench-panel input {
        border: 1px solid rgba(255, 255, 255, 0.15);
        border-radius: 0.45rem;
        background: rgba(255, 255, 255, 0.08);
        color: inherit;
        padding: 0.45rem 0.55rem;
        font: inherit;
      }
      #browserbench-panel .bb-actions {
        display: flex;
        gap: 0.5rem;
        margin-top: 0.9rem;
      }
      #browserbench-panel button {
        border: 0;
        border-radius: 999px;
        padding: 0.55rem 0.8rem;
        font: inherit;
        cursor: pointer;
        background: #f0c36d;
        color: #191919;
      }
      #browserbench-panel .bb-secondary {
        background: rgba(255, 255, 255, 0.16);
        color: #f8f4e8;
      }
      #browserbench-summary {
        display: grid;
        gap: 0.35rem;
        margin-top: 0.9rem;
      }
      #browserbench-summary .bb-row {
        display: flex;
        justify-content: space-between;
        gap: 1rem;
      }
      #browserbench-panel .bb-note {
        margin-top: 0.75rem;
        color: rgba(248, 244, 232, 0.78);
      }
    `;
    document.head.appendChild(style);

    const wrapper = document.createElement("section");
    wrapper.id = "browserbench-panel";
    wrapper.innerHTML = `
      <details open>
        <summary>BrowserBench metrics capture</summary>
        <div class="bb-grid">
          <label>Tester<input name="tester" placeholder="alice"></label>
          <label>Browser<input name="browser_label" placeholder="chrome / firefox"></label>
          <label>Device<input name="device_label" placeholder="macbook-air-m2"></label>
          <label>OS<input name="os_label" placeholder="macos-15"></label>
          <label>Network<input name="network_profile" placeholder="baseline"></label>
          <label>Cache<input name="cache_state" placeholder="cold / warm"></label>
          <label>Run #<input name="run_number" placeholder="1"></label>
          <label>Notes<input name="notes" placeholder="optional"></label>
        </div>
        <div class="bb-actions">
          <button type="button" id="bb-refresh">Refresh summary</button>
          <button type="button" id="bb-copy" class="bb-secondary">Copy JSON</button>
          <button type="button" id="bb-download">Download JSON</button>
        </div>
        <div id="browserbench-summary"></div>
        <p class="bb-note">Use this JSON as the primary cross-browser artifact. Export HAR or take DevTools screenshots separately if your browser supports them.</p>
      </details>
    `;
    document.body.appendChild(wrapper);

    wrapper.querySelector("#bb-refresh").addEventListener("click", () => renderSummary(collectPayload()));
    wrapper.querySelector("#bb-copy").addEventListener("click", () => copyPayload().catch(console.error));
    wrapper.querySelector("#bb-download").addEventListener("click", downloadPayload);
  }

  observeMetrics();
  window.addEventListener("load", () => {
    window.setTimeout(() => {
      injectPanel();
      renderSummary(collectPayload());
    }, 1200);
  });
})();
