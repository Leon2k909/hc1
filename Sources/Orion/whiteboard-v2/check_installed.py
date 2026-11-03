"""See the installed whiteboard as the scene now draws it, with nothing added: python check_installed.py <project root>

Waits for the open editor to recompile orion_fuel after the cut, since a look before that still shows the old picture. Then renders compare_whiteboard.py's views of the scene
as it is, and saves them as installed_<view>.png.
"""
import os
import subprocess
import sys
import time

ROOT = sys.argv[1]
BASE = os.path.join(ROOT, "Assets", "models", "maps", "orion")
FOLDER = os.path.join(ROOT, "output", "asset-improvement-20261030", "whiteboard")
source, built = os.path.join(BASE, "orion_fuel.obj"), os.path.join(BASE, "orion_fuel.vmdl_c")
started = time.time()
while os.path.getmtime(built) < os.path.getmtime(source):
    if time.time() - started > 480:
        print("orion_fuel still hasn't recompiled after 8 minutes", flush=True)
        sys.exit(1)
    time.sleep(10)
print(f"orion_fuel recompiled, waited {time.time() - started:.0f}s", flush=True)
time.sleep(5)
run = subprocess.run([sys.executable, os.path.join(os.path.dirname(os.path.abspath(__file__)), "compare_whiteboard.py"), ROOT, "old"], capture_output=True, text=True, timeout=200)
print(" ".join((run.stdout + run.stderr).split())[:300], flush=True)
for name in os.listdir(FOLDER):
    if name.startswith("old_") and name.endswith(".png") and os.path.getmtime(os.path.join(FOLDER, name)) > started:
        os.replace(os.path.join(FOLDER, name), os.path.join(FOLDER, "installed_" + name[4:]))
        print("wrote installed_" + name[4:], flush=True)
