"""Process-local fallback for this workstation's stalled Windows WMI provider."""
import platform
from pathlib import Path
import runpy
import sys


def unavailable_wmi(*args, **kwargs):
    raise OSError("Use the registry platform fallback for this offline build")


platform._wmi_query = unavailable_wmi
target = Path(sys.argv[1]).resolve()
sys.argv = sys.argv[1:]
sys.path.insert(0, str(target.parent))
runpy.run_path(str(target), run_name="__main__")
