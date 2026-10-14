"""Pass an existing task C# script to the connected editor without shell JSON quoting."""
import json
from pathlib import Path
import shutil
import subprocess
import sys

source = Path(sys.argv[1]).resolve()
exchange = Path("C:/Users/leon2/AppData/Local/Temp/sbox-cli/c8638b1130264085bfe2ac07cc76ff83")
exchange.mkdir(parents=True, exist_ok=True)
destination = exchange / source.name
shutil.copyfile(source, destination)
raise SystemExit(subprocess.call([
    "D:/SteamLibrary/steamapps/common/sbox/bin/managed/sbox-cli.exe", "--call", "run_csharp",
    json.dumps({"path": str(destination)}),
]))
