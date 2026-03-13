from __future__ import annotations

from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse


def _pad(text: str, target_bytes: int, filler: str) -> str:
    raw = text.encode("utf-8")
    if len(raw) >= target_bytes:
        return raw[:target_bytes].decode("utf-8", errors="ignore")
    remaining = target_bytes - len(raw)
    chunks = []
    while remaining > 0:
        piece = filler[:remaining]
        chunks.append(piece)
        remaining -= len(piece.encode("utf-8"))
    return text + "".join(chunks)


def _style_payload(kb: int, variant: str) -> str:
    base = f"""/* browserbench generated stylesheet */
:root {{
  --accent: hsl(192 74% 33%);
  --surface: hsl(48 38% 95%);
  --ink: hsl(210 22% 14%);
}}
body {{
  background: linear-gradient(180deg, white, var(--surface));
  color: var(--ink);
}}
.tile-{variant} {{
  border: 1px solid color-mix(in srgb, var(--accent) 35%, white);
  box-shadow: 0 8px 24px rgb(0 0 0 / 0.08);
  padding: 1rem;
}}
"""
    return _pad(base, kb * 1024, "/* generated-style-padding */\n")


def _script_payload(kb: int, variant: str) -> str:
    base = f"""(() => {{
  window.__browserbenchScripts = window.__browserbenchScripts || [];
  window.__browserbenchScripts.push({{ variant: "{variant}", loadedAt: performance.now() }});
  const root = document.querySelector("[data-script-target='{variant}']");
  if (root) {{
    root.textContent = `script:{variant}:` + Math.round(performance.now());
  }}
}})();
"""
    return _pad(base, kb * 1024, "// generated-script-padding\n")


def _json_payload(kb: int, variant: str) -> str:
    header = (
        "{"
        f"\"variant\":\"{variant}\","
        "\"items\":["
    )
    footer = "]}"
    body = []
    while len((header + "".join(body) + footer).encode("utf-8")) < (kb * 1024) - 32:
        body.append("\"browserbench-payload\",")
    payload = header + "".join(body).rstrip(",") + footer
    return payload


def _svg_payload(kb: int, label: str, color: str) -> str:
    base = f"""<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="800" viewBox="0 0 1200 800">
  <defs>
    <linearGradient id="g" x1="0%" x2="100%" y1="0%" y2="100%">
      <stop offset="0%" stop-color="{color}" />
      <stop offset="100%" stop-color="#f8f4e8" />
    </linearGradient>
  </defs>
  <rect width="1200" height="800" fill="url(#g)" />
  <circle cx="300" cy="280" r="180" fill="rgb(255 255 255 / 0.32)" />
  <circle cx="760" cy="420" r="240" fill="rgb(255 255 255 / 0.18)" />
  <text x="70" y="120" font-size="54" font-family="Georgia, serif" fill="#10212b">{label}</text>
  <!--
"""
    tail = "\n  -->\n</svg>\n"
    target = kb * 1024
    fill = _pad(base, target - len(tail.encode("utf-8")), "svg-padding-")
    return fill + tail


class ScenarioRequestHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, directory: str, **kwargs):
        self._scenario_directory = directory
        super().__init__(*args, directory=directory, **kwargs)

    def do_GET(self) -> None:  # noqa: N802
        self._dispatch_request(include_body=True)

    def do_HEAD(self) -> None:  # noqa: N802
        self._dispatch_request(include_body=False)

    def _dispatch_request(self, include_body: bool) -> None:
        parsed = urlparse(self.path)
        if parsed.path == "/__health":
            self._write_payload(
                b'{"status":"ok"}',
                "application/json; charset=utf-8",
                include_body=include_body,
            )
            return

        if parsed.path.startswith("/generated/"):
            self._serve_generated(parsed, include_body=include_body)
            return

        if include_body:
            super().do_GET()
        else:
            super().do_HEAD()

    def log_message(self, fmt: str, *args) -> None:  # noqa: A003
        print(f"[server] {self.address_string()} - {fmt % args}")

    def _serve_generated(self, parsed, include_body: bool) -> None:
        params = parse_qs(parsed.query)
        kb = max(1, int(params.get("kb", ["8"])[0]))
        variant = params.get("variant", ["default"])[0]
        color = params.get("color", ["#0b7285"])[0]

        if parsed.path.endswith("style.css"):
            payload = _style_payload(kb, variant).encode("utf-8")
            self._write_payload(payload, "text/css; charset=utf-8", include_body=include_body)
            return

        if parsed.path.endswith("script.js"):
            payload = _script_payload(kb, variant).encode("utf-8")
            self._write_payload(payload, "application/javascript; charset=utf-8", include_body=include_body)
            return

        if parsed.path.endswith("data.json"):
            payload = _json_payload(kb, variant).encode("utf-8")
            self._write_payload(payload, "application/json; charset=utf-8", include_body=include_body)
            return

        if parsed.path.endswith("image.svg"):
            payload = _svg_payload(kb, variant, color).encode("utf-8")
            self._write_payload(payload, "image/svg+xml; charset=utf-8", include_body=include_body)
            return

        self.send_error(HTTPStatus.NOT_FOUND, "Unknown generated asset")

    def _write_payload(self, payload: bytes, content_type: str, include_body: bool) -> None:
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(payload)))
        self.send_header("Cache-Control", "public, max-age=31536000")
        self.end_headers()
        if include_body:
            self.wfile.write(payload)


def serve(host: str, port: int, scenario_root: Path) -> None:
    handler = lambda *args, **kwargs: ScenarioRequestHandler(  # noqa: E731
        *args,
        directory=str(scenario_root),
        **kwargs,
    )
    httpd = ThreadingHTTPServer((host, port), handler)
    print(f"Serving scenarios from {scenario_root} on http://{host}:{port}")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("Shutting down benchmark server.")
    finally:
        httpd.server_close()
