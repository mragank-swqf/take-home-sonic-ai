#!/usr/bin/env bash
# Build explanation.pdf from docs/explanation.md (2–3 pages).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SRC="$ROOT/docs/explanation.md"
OUT="$ROOT/explanation.pdf"

if [[ ! -f "$SRC" ]]; then
  echo "Missing $SRC" >&2
  exit 1
fi

if command -v pandoc >/dev/null 2>&1; then
  echo "Using pandoc…"
  pandoc "$SRC" -o "$OUT" \
    --pdf-engine=xelatex \
    -V geometry:margin=0.85in \
    -V fontsize=10pt \
    -V documentclass=article \
    --metadata title="Sonic AI take-home — technical explanation" || \
  pandoc "$SRC" -o "$OUT" -V geometry:margin=0.85in -V fontsize=10pt
  echo "Wrote $OUT"
  exit 0
fi

if python3 -c "import weasyprint" 2>/dev/null || python -c "import weasyprint" 2>/dev/null; then
  echo "Using weasyprint…"
  PY=python3
  command -v python3 >/dev/null 2>&1 || PY=python
  "$PY" - <<'PY'
from pathlib import Path
import markdown
from weasyprint import HTML
root = Path(__file__).resolve().parents[1] if False else Path.cwd()
# script may be invoked from repo root via bash; resolve via env
import os
root = Path(os.environ.get("ROOT", Path.cwd()))
src = root / "docs" / "explanation.md"
html = markdown.markdown(src.read_text(encoding="utf-8"), extensions=["tables", "fenced_code"])
styled = f"""<!doctype html><html><head><meta charset='utf-8'>
<style>
body {{ font-family: Helvetica, Arial, sans-serif; font-size: 10pt; line-height: 1.35; margin: 0.85in; }}
h1 {{ font-size: 14pt; }} h2 {{ font-size: 11pt; margin-top: 0.7em; }}
table {{ border-collapse: collapse; width: 100%; font-size: 9pt; }}
th, td {{ border: 1px solid #999; padding: 3px 5px; vertical-align: top; }}
code, pre {{ font-size: 9pt; }}
pre {{ background: #f4f4f4; padding: 6px; }}
</style></head><body>{html}</body></html>"""
HTML(string=styled).write_pdf(root / "explanation.pdf")
print("Wrote", root / "explanation.pdf")
PY
  exit 0
fi

echo "pandoc/weasyprint unavailable — using Python fpdf2 fallback…"
cd "$ROOT"
python scripts/build_pdf.py || python3 scripts/build_pdf.py
