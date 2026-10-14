"""Summarize the three final in-engine window captures and preview cleanup."""
import json
from pathlib import Path
import re

folder = Path(__file__).resolve().parent
rows = []
for name in ("live-canal-interior-windows", "live-sealed-window-final", "live-sealed-window-grazing"):
    text = (folder / (name + "-diagnostics.txt")).read_text()
    models = re.findall(r"^(.+): modelError=(\w+); materialErrors=(\d+)$", text, re.M)
    assert len(models) >= 11
    assert all(error == "False" and count == "0" for _, error, count in models)
    assert text.count("downwardClear=True") == 18
    assert "Lights: points=24; spots=0" in text
    assert (folder / (name + ".png")).exists()
    rows.append(f"PASS {name}: {len(models)} model renderers, zero model/material errors; 18 light emitters clear")
assert json.loads((folder / "window-cleanup-check.json").read_text())["remainingQaScenes"] == []
rows.append("PASS: all temporary Lowtide QA scenes were destroyed")
(folder / "window-render-checks.txt").write_text("\n".join(rows) + "\n")
print("\n".join(rows))
