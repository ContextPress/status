# Newdle Status

Public status page for [status.newdle.com](https://status.newdle.com), hosted on GitHub Pages.

The page fetches `status.json` every 60 seconds and renders the current state of Newdle's systems. Pushing a change to `main` is all it takes to update what users see.

---

## Files

| File | Purpose |
|---|---|
| `index.html` | The public status page. Fetches `status.json` and renders it with vanilla JS. |
| `status.json` | Machine-readable payload that drives the page. Edit this to change what users see. |
| `outage.html` | A standalone "we'll be right back" page. No JS, no fetch — used when you want to serve a hard-coded message at the DNS/CDN level during a full outage. |
| `CNAME` | Custom domain record (`status.newdle.com`) for GitHub Pages. |

---

## Updating Status

### Preferred: use the admin tool

```bash
python3 admin.py
```

Opens a local form at [http://localhost:8765](http://localhost:8765) via `admin.py`. Fill in the fields and click **Save & Push** — it writes `status.json`, commits, and pushes to `main` automatically.

### Manual: edit and push

```bash
# Edit status.json directly, then:
git add status.json
git commit -m "chore: update status [operational]"
git push origin main
```

---

## `status.json` Schema

```jsonc
{
  // Required booleans — only one should be true at a time.
  // maintenance takes precedence over degraded.
  "maintenance": false,
  "degraded": false,

  // Optional — headline shown in the status banner.
  // Defaults to "All Systems Operational" / "Partial Disruption" / "Under Maintenance".
  "title": "Newdle is down for maintenance.",

  // Optional — body copy shown below the title.
  "message": "We'll be back soon.",

  // Optional — ISO 8601 UTC. Shown as "Estimated recovery: ..." when degraded or down.
  "estimated_end": "2026-05-07T22:00:00Z",

  // Optional — ISO 8601 UTC. Recorded metadata; not rendered in the UI.
  "updated_at": "2026-05-07T18:49:00Z",

  // Optional — per-service status badges.
  "services": [
    { "name": "API",  "status": "operational" },
    { "name": "Web",  "status": "degraded" },
    { "name": "Auth", "status": "down" }
  ],

  // Optional — incident history cards shown below the banner.
  "incidents": [
    {
      "title": "API latency spike",
      "date": "2026-05-06T14:00:00Z",
      "status": "resolved",       // resolved | monitoring | investigating
      "body": "Elevated p99 latency due to a database index rebuild. Now resolved."
    }
  ]
}
```

### State logic

| Condition | UI state | Banner color |
|---|---|---|
| `maintenance: true` | Down | Red |
| `degraded: true` (and not maintenance) | Degraded | Amber |
| Both false | Operational | Green |

---

## Deployment

Push to `main` → GitHub Pages rebuilds automatically (no build step, it's just static files). The live page at `status.newdle.com` will reflect the change within seconds; browsers already on the page pick it up at the next 60-second poll.

### GitHub Pages config

Repository: [ContextPress/status](https://github.com/ContextPress/status)
Branch: `main` / root
Custom domain: `status.newdle.com` (set in `CNAME`)

---

## `outage.html`

A fully static fallback page with no dependencies. Use it when Newdle is completely unreachable and you want to serve a hard-coded message at the DNS or CDN level — e.g. point your CDN origin at this file directly, or serve it from a separate host. It does not read `status.json`.
