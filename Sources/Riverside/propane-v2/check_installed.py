"""See the installed propane cylinders as the scene now draws them, with nothing added: python check_installed.py <project root>

Waits for the open editor to recompile the pad's and the terrace's models after the cut, since a look before that still shows the old cylinders. Then renders
compare_propane.py's views of the pad's row and the camper's pair as the scene stands, and saves them as installed_<view>.png. The old shots are kept as
before_<view>.png first.
"""
import os
import shutil
import subprocess
import sys
import time

ROOT = sys.argv[1]
BASE = os.path.join(ROOT, "Assets", "models", "maps", "riverside")
FOLDER = os.path.join(ROOT, "output", "asset-improvement-20261030", "propane")
started = time.time()
for name in ("riverside_pad", "riverside_terrace"):
    source, built = os.path.join(BASE, name + ".obj"), os.path.join(BASE, name + ".vmdl_c")
    while os.path.getmtime(built) < os.path.getmtime(source):
        if time.time() - started > 900:
            print(name, "still hasn't recompiled after 15 minutes", flush=True)
            sys.exit(1)
        time.sleep(10)
    print(f"{name} recompiled, waited {time.time() - started:.0f}s", flush=True)
time.sleep(5)
for name in os.listdir(FOLDER):
    if name.startswith("old_") and name.endswith(".png") and not os.path.exists(os.path.join(FOLDER, "before_" + name[4:])):
        shutil.copy2(os.path.join(FOLDER, name), os.path.join(FOLDER, "before_" + name[4:]))
begun = time.time()
for which in ("row", "pair"):
    run = subprocess.run([sys.executable, os.path.join(os.path.dirname(os.path.abspath(__file__)), "compare_propane.py"), ROOT, "old", which], capture_output=True, text=True, timeout=200)
    print(which, " ".join((run.stdout + run.stderr).split())[:200], flush=True)
for name in os.listdir(FOLDER):
    if name.startswith("old_") and name.endswith(".png") and os.path.getmtime(os.path.join(FOLDER, name)) > begun:
        os.replace(os.path.join(FOLDER, name), os.path.join(FOLDER, "installed_" + name[4:]))
        print("wrote installed_" + name[4:], flush=True)
