"""Offline material/composition preview. Native s&box captures remain authoritative."""
from pathlib import Path
import platform
import sys

def unavailable_wmi(*args, **kwargs):
    raise OSError("WMI unavailable during this build")

platform._wmi_query = unavailable_wmi
root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(root / "Tools"))
import railhead_render as render
render.SCENE = root / "output/collider/stage/collider.scene.json"
render.REFERENCE_VIEWS = [("collider",(-1050,-760,320),(470,550,360),88)]
render.main()
