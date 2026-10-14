import json
import sys
from pathlib import Path

config = json.loads(Path('Sources/Belltower/editor/capture-config.json').read_text())
config.update(directory=sys.argv[1], exclude_roots=sys.argv[2:], views=['council_hall'], width=1280, height=720)
Path('output/belltower/quality/capture-config.json').write_text(json.dumps(config, indent=2))
