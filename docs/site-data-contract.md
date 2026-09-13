# Site data contract

The public dashboard is a static site in `public/`: `index.html`, `app.js` and JSON under
`public/data/`. Anything that writes data goes through `tools/site_data.py`, which validates
every card. The page only reads these files.

## `public/data/YYYY-MM-DD.json`

One file per article date (the date the source published it), newest item first.

```json
{
  "date": "2026-09-04",
  "items": [
    {
      "id": "3f2a9c1b7d4e",
      "date": "2026-09-04",
      "published_at": "2026-09-04T16:05:00-04:00",
      "headline": {"en": "…", "zh": "…"},
      "summary":  {"en": "Two to three sentences.", "zh": "…"},
      "gps": ["otf", "blue_owl"],
      "sectors": ["private_credit", "software"],
      "region": "US",
      "source": {"publisher": "Blue Owl Technology Finance Corp.", "url": "https://…"},
      "review_status": "reviewed",
      "origin": "analyst_labeled"
    }
  ]
}
```

- `id`: first 12 hex characters of SHA-256 of the lower-cased source URL (no fragment or
  trailing slash). Used for de-duplication.
- `published_at`: ISO timestamp or `null`.
- `gps` / `sectors`: ids from `config/filter_rules.json`; at least one of the two is non-empty.
- `region`: `US`, `Europe`, `APAC` or `Global`.
- `review_status`: `reviewed` (analyst-approved) or `unreviewed` (auto-fetched, shown with a badge).
- `origin`: `analyst_labeled` or `auto_fetch`.

## `public/data/index.json`

```json
{
  "generated_at": "2026-09-13T12:00:00+00:00",
  "window_days": 90,
  "dates": ["2026-09-12", "2026-09-11"],
  "counts": {"2026-09-12": 4, "2026-09-11": 7},
  "labels": {
    "gps": {"otf": {"en": "OTF (Blue Owl Technology Finance)", "zh": "OTF（Blue Owl 科技金融）"}},
    "sectors": {"clo": {"en": "CLO", "zh": "CLO"}},
    "regions": {"US": {"en": "US", "zh": "美国"}}
  }
}
```

`dates` lists only days with at least one item, newest first. Days older than `window_days` are
deleted on each refresh.

## `public/data/status.json`

```json
{
  "mode": "scheduled",
  "schedule": {"en": "Refreshes automatically on weekdays at 08:00 and 16:00 Hong Kong time", "zh": "…"},
  "last_refresh_at": "2026-09-13T08:00:12+00:00",
  "last_refresh_result": "succeeded",
  "last_success_at": "2026-09-13T08:00:12+00:00",
  "new_items": 5,
  "detail": null
}
```

`last_refresh_result` is `succeeded`, `no_new_items` or `failed`; a failed refresh keeps the
previous `last_success_at`.

## `public/data/seen.json`

`{"ids": {"3f2a9c1b7d4e": "2026-09-13"}}`: card ids of auto-fetched items the model rejected, with
the day they were rejected. Kept for 14 days so scheduled runs do not brief the same item twice.
The page does not read it.
