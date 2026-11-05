"""Use native one-shot script execution when the persistent connection times out."""
from pathlib import Path
import sys,json
from native import call
print(json.dumps(call('run_csharp',{'code':Path(sys.argv[1]).read_text()}),indent=2))
