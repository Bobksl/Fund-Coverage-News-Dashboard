# Fund Coverage News Dashboard

A daily, bilingual (English / 中文) news page for Junson Capital's alternative-credit portfolio:
13 tracked managers and 8 sub-sectors, US-focused with European coverage.

- **Live page:** https://bobksl.github.io/Fund-Coverage-News-Dashboard/
- **Delivery note** (how it updates, filtering logic, limitations): [DELIVERY.md](DELIVERY.md)

## Layout

| Path | Purpose |
|---|---|
| [public/](public/) | The static website served by GitHub Pages: `index.html`, `app.js`, `data/` |
| [config/filter_rules.json](config/filter_rules.json) | Managers, sub-sectors, keywords, feeds and schedule |
| [tools/fetch_news.py](tools/fetch_news.py) | Scheduled refresh: fetch, filter, summarize, write cards |
| [tools/summarize.py](tools/summarize.py) | DeepSeek bilingual summary and tagging |
| [tools/site_data.py](tools/site_data.py) | Card validation, per-day files, index, status, 90-day window |
| [tools/build_site.py](tools/build_site.py) | Backfill of the analyst-reviewed history (needs local `work/`) |
| [.github/workflows/refresh.yml](.github/workflows/refresh.yml) | Weekday 08:00 / 16:00 HKT refresh and Pages deploy |
| [docs/site-data-contract.md](docs/site-data-contract.md) | JSON shapes the page reads |
| [docs/editorial-rulebook.md](docs/editorial-rulebook.md), [config/entities.json](config/entities.json), [config/sectors.json](config/sectors.json) | Editorial definitions: credit scope per manager, sub-sector inclusion rules, scoring design |

The earlier research pipeline (`tools/classifier.py`, `runner.py`, `manual_update.py`, `publication.py`
and the `site/` prototype) remains for reference. Its full history, including phase logs and
handovers, is preserved at tag `research-archive-2026-09-13`.

## Run locally

Python 3.13, standard library only.

```bash
python -m pytest -q
```

```bash
python -m tools.fetch_news --dry-run
```

```bash
python -m http.server 8000 --directory public
```

A real refresh (`python -m tools.fetch_news`) needs `DEEPSEEK_API_KEY` in the environment or a
git-ignored `.env`. In GitHub it is stored as a repository secret.

## Working boundaries

- The repository is public: never commit actual positions, private mandate details, credentials or
  full article text. Cards hold our own short summaries and a link to the source.
- No paywall bypass; sources are public feeds and pages.
