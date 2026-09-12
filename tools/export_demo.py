"""Export a minimal, isolated demo bundle: UI plus approved/candidate edition JSON only.

Serving the repository root (the documented `python -m http.server` from earlier phases) binds
beyond localhost by default and exposes `work/`, evaluator files and everything else in the
repo. This writes a self-contained directory under `work/demo-export/` (ignored by git) that
contains only `index.html`, `app.js` and the demo-feed JSON under `data/`, and prints the
127.0.0.1-only command to serve exactly that directory and nothing else.

No labels, raw model outputs, evaluator files or credentials are copied here -- only what
tools/build_demo_feed.py already wrote to work/phase2/demo-feed/, which itself never reads gold.
"""
import argparse
import shutil
from pathlib import Path

from tools import build_demo_feed

ROOT = Path(__file__).resolve().parent.parent
SITE_DIR = ROOT / "site"
DEFAULT_EXPORT_DIR = ROOT / "work/demo-export"
SITE_FILES = ("index.html", "app.js")


def export(export_dir=DEFAULT_EXPORT_DIR, rebuild_feed=True):
    export_dir = Path(export_dir)
    if rebuild_feed:
        build_demo_feed.build()
    if export_dir.exists():
        shutil.rmtree(export_dir)
    export_dir.mkdir(parents=True)
    for name in SITE_FILES:
        shutil.copy2(SITE_DIR / name, export_dir / name)
    data_dir = export_dir / "data"
    shutil.copytree(build_demo_feed.OUT_DIR, data_dir)
    copied = sorted(p.name for p in data_dir.glob("*.json"))
    return {"export_dir": str(export_dir), "site_files": list(SITE_FILES),
            "data_files": len(copied), "serve_command":
            f"python -m http.server 8642 --bind 127.0.0.1 --directory \"{export_dir}\""}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--export-dir", type=Path, default=DEFAULT_EXPORT_DIR)
    parser.add_argument("--no-rebuild", action="store_true",
                        help="Skip regenerating work/phase2/demo-feed before exporting")
    args = parser.parse_args(argv)
    result = export(args.export_dir, rebuild_feed=not args.no_rebuild)
    print(f"Exported {result['data_files']} data files and {len(result['site_files'])} site "
         f"files to {result['export_dir']}.")
    print(f"Serve with: {result['serve_command']}")
    print(f"Then open: http://127.0.0.1:8642/index.html")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
