"""Attach to the existing editor; keep this phone's logs and clean owned exchange scripts."""
from pathlib import Path
import sys
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2]
sys.path.insert(0,str(ROOT/'Sources/Collider/tool-cabinet-trial-v1'))
# Import by path because this wrapper deliberately shares the CLI module's basename.
import importlib.util
spec=importlib.util.spec_from_file_location('phone_native_transport',ROOT/'Sources/Collider/tool-cabinet-trial-v1/native_cli.py')
native=importlib.util.module_from_spec(spec);spec.loader.exec_module(native)
native.OUT=ROOT/'output/riverdale-emergency-phone-review-20261031/native';native.OUT.mkdir(parents=True,exist_ok=True)
original_close=native.Client.close
def close(client):
    directory=Path(client.initial['_meta']['exchangeDirectory'])
    original_close(client)
    if len(sys.argv)>2 and sys.argv[1]=='script':
        source=Path(sys.argv[2]);owned=directory/source.name
        if owned.exists() and owned.read_bytes()==source.read_bytes():
            owned.unlink()
            if directory.exists() and not any(directory.iterdir()):directory.rmdir()
native.Client.close=close
if __name__=='__main__':native.main()
