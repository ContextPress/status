# Context: ContextPress/status

This document is written for AI assistants working in this repository. It describes what the project does, how every part works, and how to make changes correctly.

---

## What this repo is

A minimal static status and maintenance page for **Newdle** (`https://newdle.app`), served at **https://status.newdle.com** via GitHub Pages.

There is no build step, no framework, and no package manager. Everything is plain HTML, CSS, and vanilla JavaScript. The only dynamic data is `status.json`, which the page fetches from the server every 60 seconds.

---

## Repository structure

```
/
├── index.html      Main status page. Fetches status.json and renders it.
├── status.json     The live data payload. Edit this to change what users see.
├── outage.html     A static fallback page. No JS. Used at the DNS/CDN level during full outages.
├── CNAME           Custom domain: status.newdle.com
├── README.md       Engineer documentation.
└── .ai/
    └── context.md  This file.
```

`admin.py` is committed to the repo. Engineers clone the repo and run it locally — it is never executed by GitHub Pages (browsers treat it as a plain text download).

---

## How the status page works

`index.html` runs a `fetch('./status.json?t=<timestamp>')` on load, then repeats every 60 seconds (`REFRESH_MS = 60_000`). The response is parsed and passed to a `render(data)` function that builds the page DOM.

### State computation

```js
function state(data) {
  if (data.maintenance) return 'down';
  if (data.degraded)    return 'warn';
  return 'ok';
}
```

`maintenance` takes precedence. Both flags should not be `true` at the same time.

### State → UI mapping

| state value | Banner color | Eyebrow label | Dot animation |
|---|---|---|---|
| `ok` | Green | Operational | Pulsing green |
| `warn` | Amber | Degraded | Static amber |
| `down` | Red | Maintenance | Pulsing red |

### Default titles (when `title` is omitted from status.json)

```js
function defaultTitle(s) {
  if (s === 'down') return 'Under Maintenance';
  if (s === 'warn') return 'Partial Disruption';
  return 'All Systems Operational';
}
```

### Estimated recovery display

`estimated_end` is only rendered when `state` is `warn` or `down`. If state is `ok`, the field is ignored even if present.

---

## `status.json` schema

All fields are at the root level. The file must be valid JSON.

### Required

| Field | Type | Description |
|---|---|---|
| `maintenance` | boolean | `true` → down state (red, highest priority) |
| `degraded` | boolean | `true` → warn state (amber), only when `maintenance` is `false` |

### Optional

| Field | Type | Description |
|---|---|---|
| `title` | string | Headline in the status banner. Defaults to a state-based label if absent. |
| `message` | string | Body copy shown below the title. Omit to show nothing. |
| `estimated_end` | string (ISO 8601 UTC) | "Estimated recovery" time. Shown only when state is warn or down. Example: `"2026-05-07T22:00:00Z"` |
| `updated_at` | string (ISO 8601 UTC) | Metadata timestamp. Not rendered in the UI. The admin tool sets this automatically on every save. |
| `services` | array | Per-service status rows. See below. |
| `incidents` | array | Incident history cards. See below. |

### `services[]` items

```jsonc
{
  "name": "API",          // Display name
  "status": "operational" // "operational" → green badge
                          // "degraded"    → amber badge
                          // anything else → red badge (treated as "down")
}
```

### `incidents[]` items

```jsonc
{
  "title": "API latency spike",        // Incident headline (Fraunces serif font)
  "date": "2026-05-06T14:00:00Z",      // ISO 8601 UTC, formatted by toLocaleString
  "status": "resolved",                // resolved | monitoring | investigating
                                       // Controls the dot color: resolved=green, monitoring=amber, investigating=red
                                       // Defaults to "resolved" if omitted
  "body": "Details about the incident." // Muted body text
}
```

---

## How to update status

### With the admin tool (preferred)

```bash
python3 admin.py
# Open http://localhost:8765
```

Fill in the form and click "Save & Push". The tool:
1. Writes `status.json`
2. Runs `git add status.json`
3. Runs `git commit -m "chore: update status [<state>]"`
4. Runs `git push origin main`

### Manually

1. Edit `status.json` directly.
2. `git add status.json && git commit -m "chore: update status [operational]" && git push origin main`

---

## Deployment

- **Host**: GitHub Pages
- **Repository**: `ContextPress/status` on GitHub
- **Branch**: `main`, root directory
- **Custom domain**: `status.newdle.com` (set in `CNAME`)
- **SSH remote**: `git@github.com:ContextPress/status.git`

Pushing to `main` deploys instantly — GitHub Pages serves the updated files within seconds. There is no CI, no build pipeline, and no CDN cache to invalidate.

---

## `outage.html`

A fully self-contained HTML page: no `fetch`, no external JS, no reference to `status.json`. It displays a hard-coded "we'll be right back" message. Use it when the main app is entirely unreachable — point a CDN origin or load balancer directly at this file, or use a DNS-level redirect, so users see something meaningful even if GitHub Pages itself were down.

---

## What not to do

- Do not add a build step or package manager without updating this document and the README.
- Do not add fields to `status.json` without updating both `index.html` (to render them) and this document.
- Do not remove `admin.py` from the repo — other engineers depend on it being there when they clone.
- Do not edit `outage.html` to add a `fetch` to `status.json` — its value is that it has zero runtime dependencies.
