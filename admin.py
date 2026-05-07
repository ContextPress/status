#!/usr/bin/env python3
"""
Local admin server for status.newdle.com.
Updates status.json, commits, and pushes to origin/main.

Usage: python3 admin.py
       Then open http://localhost:8765
"""

import http.server
import json
import os
import subprocess
import urllib.parse
from datetime import datetime, timezone
from pathlib import Path

PORT = 8765
REPO_ROOT = Path(__file__).parent.resolve()
STATUS_FILE = REPO_ROOT / "status.json"

OPERATIONAL_TITLE = "Newdle is doing well."
OPERATIONAL_MESSAGE = "We know you depend on Newdle, so we're always keeping an eye on it."


def read_status():
    try:
        return json.loads(STATUS_FILE.read_text())
    except Exception:
        return {}


def state_label(data):
    if data.get("maintenance"):
        return "maintenance"
    if data.get("degraded"):
        return "degraded"
    return "operational"


def iso_to_local_input(iso):
    """Convert ISO 8601 UTC string to datetime-local input value (YYYY-MM-DDTHH:MM)."""
    if not iso:
        return ""
    try:
        dt = datetime.fromisoformat(iso.replace("Z", "+00:00"))
        # Convert to local machine time for the input
        local_dt = dt.astimezone()
        return local_dt.strftime("%Y-%m-%dT%H:%M")
    except Exception:
        return ""


def local_input_to_iso(value):
    """Convert datetime-local input value to ISO 8601 UTC string."""
    if not value:
        return ""
    try:
        dt = datetime.fromisoformat(value).astimezone(timezone.utc)
        return dt.strftime("%Y-%m-%dT%H:%M:%SZ")
    except Exception:
        return value


def render_form(data, flash=None, error=None):
    state = state_label(data)
    title = OPERATIONAL_TITLE if state == "operational" else data.get("title", "")
    message = OPERATIONAL_MESSAGE if state == "operational" else data.get("message", "")

    estimated_end = iso_to_local_input(data.get("estimated_end", ""))
    is_operational = state == "operational"
    msg_readonly = 'readonly' if is_operational else ''
    msg_locked_class = ' locked' if is_operational else ''

    def checked(s):
        return 'checked' if state == s else ''

    flash_html = ""
    if flash:
        flash_html = f'<div class="flash ok">{flash}</div>'
    if error:
        flash_html = f'<div class="flash err">{error}</div>'

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>Status Admin — newdle</title>
  <style>
    *, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}

    :root {{
      --bg:       #FAF8F3;
      --surface:  #F3EFE5;
      --border:   rgba(60,45,20,0.14);
      --text:     #1A1612;
      --muted:    #7A6E60;
      --accent:   #E8533A;
      --green-bg: #EAF4EC;
      --green-fg: #1D6B35;
      --amber-bg: #FFF4DE;
      --amber-fg: #8C5A00;
      --red-bg:   #FDECEA;
      --red-fg:   #9B2B25;
      --radius:   10px;
    }}

    body {{
      background: var(--bg);
      color: var(--text);
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
      font-size: 15px;
      line-height: 1.5;
      min-height: 100vh;
      display: flex;
      flex-direction: column;
      align-items: center;
      padding: 2.5rem 1.25rem 4rem;
    }}

    .container {{ width: 100%; max-width: 560px; }}

    header {{
      display: flex;
      align-items: baseline;
      gap: 0.5rem;
      margin-bottom: 2rem;
    }}

    .wordmark {{
      font-size: 1.35rem;
      font-weight: 600;
      letter-spacing: -0.02em;
      color: var(--text);
      text-decoration: none;
    }}

    .badge {{
      font-size: 0.7rem;
      font-weight: 500;
      letter-spacing: 0.07em;
      text-transform: uppercase;
      color: var(--muted);
      background: var(--surface);
      border: 1px solid var(--border);
      border-radius: 100px;
      padding: 0.15em 0.65em;
    }}

    .flash {{
      border-radius: var(--radius);
      padding: 0.75rem 1rem;
      font-size: 0.875rem;
      margin-bottom: 1.25rem;
    }}
    .flash.ok  {{ background: var(--green-bg); color: var(--green-fg); }}
    .flash.err {{ background: var(--red-bg);   color: var(--red-fg); }}

    .card {{
      background: var(--surface);
      border-radius: var(--radius);
      border: 1px solid var(--border);
      padding: 1.5rem;
      margin-bottom: 1rem;
    }}

    .card-title {{
      font-size: 0.7rem;
      font-weight: 600;
      letter-spacing: 0.1em;
      text-transform: uppercase;
      color: var(--muted);
      margin-bottom: 1rem;
    }}

    .status-options {{
      display: grid;
      grid-template-columns: repeat(3, 1fr);
      gap: 0.5rem;
    }}

    .status-option input[type=radio] {{ display: none; }}

    .status-option label {{
      display: block;
      text-align: center;
      padding: 0.6rem 0.5rem;
      border-radius: 8px;
      border: 2px solid var(--border);
      background: var(--bg);
      font-size: 0.875rem;
      font-weight: 500;
      cursor: pointer;
      transition: border-color 0.15s, background 0.15s;
    }}

    .status-option input[value=operational]:checked + label {{
      border-color: #2A9E4F;
      background: var(--green-bg);
      color: var(--green-fg);
    }}
    .status-option input[value=degraded]:checked + label {{
      border-color: #C17D0A;
      background: var(--amber-bg);
      color: var(--amber-fg);
    }}
    .status-option input[value=maintenance]:checked + label {{
      border-color: #C13A33;
      background: var(--red-bg);
      color: var(--red-fg);
    }}

    .field {{ margin-bottom: 1rem; }}
    .field:last-child {{ margin-bottom: 0; }}

    label.field-label {{
      display: block;
      font-size: 0.8rem;
      font-weight: 500;
      color: var(--muted);
      margin-bottom: 0.35rem;
    }}

    input[type=text],
    input[type=datetime-local],
    textarea {{
      width: 100%;
      padding: 0.55rem 0.75rem;
      border: 1px solid var(--border);
      border-radius: 8px;
      background: var(--bg);
      color: var(--text);
      font-family: inherit;
      font-size: 0.9375rem;
      transition: border-color 0.15s;
      outline: none;
    }}

    input[type=text]:focus,
    input[type=datetime-local]:focus,
    textarea:focus {{
      border-color: var(--accent);
    }}

    textarea {{
      resize: vertical;
      min-height: 90px;
    }}

    .hint {{
      font-size: 0.75rem;
      color: var(--muted);
      margin-top: 0.3rem;
    }}

    input[readonly],
    textarea[readonly] {{
      opacity: 0.5;
      cursor: not-allowed;
    }}

    .locked-note {{
      font-size: 0.75rem;
      color: var(--muted);
      margin-top: 0.3rem;
      font-style: italic;
    }}

    .actions {{
      display: flex;
      gap: 0.75rem;
      align-items: center;
      margin-top: 1.25rem;
    }}

    button[type=submit] {{
      background: var(--accent);
      color: #fff;
      border: none;
      border-radius: 8px;
      padding: 0.65rem 1.4rem;
      font-size: 0.9375rem;
      font-weight: 500;
      cursor: pointer;
      transition: opacity 0.15s;
    }}
    button[type=submit]:hover {{ opacity: 0.88; }}
    button[type=submit]:active {{ opacity: 0.75; }}

    .preview-link {{
      font-size: 0.8125rem;
      color: var(--muted);
      text-decoration: none;
    }}
    .preview-link:hover {{ color: var(--text); }}

    footer {{
      margin-top: 2.5rem;
      font-size: 0.75rem;
      color: var(--muted);
      text-align: center;
    }}
  </style>
</head>
<body>
  <div class="container">
    <header>
      <span class="wordmark">newdle</span>
      <span class="badge">Status Admin</span>
    </header>

    {flash_html}

    <form method="POST" action="/save">
      <div class="card">
        <p class="card-title">Current Status</p>
        <div class="status-options">
          <div class="status-option">
            <input type="radio" name="state" id="s-operational" value="operational" {checked('operational')} />
            <label for="s-operational">Operational</label>
          </div>
          <div class="status-option">
            <input type="radio" name="state" id="s-degraded" value="degraded" {checked('degraded')} />
            <label for="s-degraded">Degraded</label>
          </div>
          <div class="status-option">
            <input type="radio" name="state" id="s-maintenance" value="maintenance" {checked('maintenance')} />
            <label for="s-maintenance">Maintenance</label>
          </div>
        </div>
      </div>

      <div class="card">
        <p class="card-title">Message</p>

        <div class="field">
          <label class="field-label" for="f-title">Title</label>
          <input type="text" id="f-title" name="title" value="{title}"
                 placeholder="Leave blank for default based on status" {msg_readonly} />
          <p class="locked-note" id="title-locked-note" style="{'display:none' if not is_operational else ''}">
            Fixed for Operational status.
          </p>
        </div>

        <div class="field">
          <label class="field-label" for="f-message">Message</label>
          <textarea id="f-message" name="message"
                    placeholder="Optional detail shown below the title" {msg_readonly}>{message}</textarea>
          <p class="locked-note" id="message-locked-note" style="{'display:none' if not is_operational else ''}">
            Fixed for Operational status.
          </p>
        </div>

        <div class="field">
          <label class="field-label" for="f-eta">Estimated Recovery</label>
          <input type="datetime-local" id="f-eta" name="estimated_end" value="{estimated_end}" />
          <p class="hint">Shown on the status page when degraded or down. Leave blank to hide.</p>
        </div>
      </div>

      <div class="actions">
        <button type="submit">Save &amp; Push</button>
        <a class="preview-link" href="https://status.newdle.com" target="_blank" rel="noopener">
          View live site &rarr;
        </a>
      </div>
    </form>

    <footer>
      Saves status.json &rarr; commits &rarr; pushes to origin/main &bull;
      <a href="https://github.com/ContextPress/status" target="_blank" rel="noopener" style="color:inherit">ContextPress/status</a>
    </footer>
  </div>

  <script>
    const OPERATIONAL_TITLE = {json.dumps(OPERATIONAL_TITLE)};
    const OPERATIONAL_MESSAGE = {json.dumps(OPERATIONAL_MESSAGE)};

    const titleInput   = document.getElementById('f-title');
    const messageInput = document.getElementById('f-message');
    const titleNote    = document.getElementById('title-locked-note');
    const messageNote  = document.getElementById('message-locked-note');
    const radios       = document.querySelectorAll('input[name=state]');

    function applyState(state) {{
      const locked = state === 'operational';
      titleInput.readOnly   = locked;
      messageInput.readOnly = locked;
      titleNote.style.display   = locked ? '' : 'none';
      messageNote.style.display = locked ? '' : 'none';
      if (locked) {{
        titleInput.value   = OPERATIONAL_TITLE;
        messageInput.value = OPERATIONAL_MESSAGE;
      }}
    }}

    radios.forEach(r => r.addEventListener('change', () => applyState(r.value)));
  </script>
</body>
</html>"""


class AdminHandler(http.server.BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        print(f"  {self.address_string()} {format % args}")

    def send_html(self, html, status=200):
        body = html.encode()
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def redirect(self, location):
        self.send_response(303)
        self.send_header("Location", location)
        self.end_headers()

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        qs = urllib.parse.parse_qs(parsed.query)

        if parsed.path == "/":
            data = read_status()
            flash = qs.get("flash", [None])[0]
            error = qs.get("error", [None])[0]
            self.send_html(render_form(data, flash=flash, error=error))
        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        if self.path != "/save":
            self.send_response(404)
            self.end_headers()
            return

        length = int(self.headers.get("Content-Length", 0))
        raw = self.rfile.read(length).decode()
        params = urllib.parse.parse_qs(raw, keep_blank_values=True)

        def get(key):
            return params.get(key, [""])[0].strip()

        state = get("state") or "operational"
        if state == "operational":
            title = OPERATIONAL_TITLE
            message = OPERATIONAL_MESSAGE
        else:
            title = get("title")
            message = get("message")
        estimated_end_raw = get("estimated_end")
        estimated_end = local_input_to_iso(estimated_end_raw)
        updated_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

        new_data = {
            "maintenance": state == "maintenance",
            "degraded": state == "degraded",
        }
        if title:
            new_data["title"] = title
        if message:
            new_data["message"] = message
        if estimated_end:
            new_data["estimated_end"] = estimated_end
        new_data["updated_at"] = updated_at

        # Write status.json
        try:
            STATUS_FILE.write_text(json.dumps(new_data, indent=2) + "\n")
        except Exception as e:
            self.redirect(f"/?error={urllib.parse.quote(f'Failed to write status.json: {e}')}")
            return

        # Git operations
        commit_msg = f"chore: update status [{state}]"
        try:
            subprocess.run(
                ["git", "add", "status.json"],
                cwd=REPO_ROOT, check=True, capture_output=True
            )
            result = subprocess.run(
                ["git", "diff", "--cached", "--quiet"],
                cwd=REPO_ROOT, capture_output=True
            )
            if result.returncode == 0:
                # Nothing staged — status.json was unchanged
                self.redirect("/?flash=" + urllib.parse.quote("No changes detected — status.json was already up to date."))
                return

            subprocess.run(
                ["git", "commit", "-m", commit_msg],
                cwd=REPO_ROOT, check=True, capture_output=True
            )
            subprocess.run(
                ["git", "push", "origin", "main"],
                cwd=REPO_ROOT, check=True, capture_output=True
            )
        except subprocess.CalledProcessError as e:
            stderr = e.stderr.decode().strip() if e.stderr else ""
            msg = f"Git error: {stderr or str(e)}"
            self.redirect(f"/?error={urllib.parse.quote(msg)}")
            return

        self.redirect("/?flash=" + urllib.parse.quote(f"Saved and pushed. Status: {state}."))


def main():
    server = http.server.HTTPServer(("127.0.0.1", PORT), AdminHandler)
    print(f"Status admin running at http://localhost:{PORT}")
    print(f"Repo: {REPO_ROOT}")
    print("Press Ctrl+C to stop.\n")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")


if __name__ == "__main__":
    main()
