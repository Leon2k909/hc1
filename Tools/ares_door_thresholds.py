"""Solid, flush thresholds across the four upper hall-to-wing openings."""
from pathlib import Path
import json

ROOT = Path(__file__).resolve().parents[1]


def scene_objects():
    return json.loads((ROOT / 'Sources/Ares/doorway-thresholds-v1/thresholds.json').read_text())
