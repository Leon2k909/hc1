"""Approved shared reel; native serialization preserves its installed transform."""
import json
from pathlib import Path
def scene_object():
    return json.loads((Path(__file__).resolve().parents[1]/'Sources/Riverdale/shared-reel-v1/native-instance.json').read_text())
