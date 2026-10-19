"""Resume-safe single-threaded native compilation of parcel-v4 forest models."""
import json
import os
from pathlib import Path
import subprocess
import winreg

ROOT = Path(__file__).resolve().parents[1]
LIST = ROOT/'output/belltower/quality/parcel-v4-model-list.txt'
LOG = ROOT/'output/belltower/quality/parcel-v4-model-compile.json'


def main():
    engine=os.getenv('FACEPUNCH_ENGINE')
    if not engine:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER,'Environment') as key:
            engine=winreg.QueryValueEx(key,'FACEPUNCH_ENGINE')[0]
    cli=Path(engine)/'bin/managed/sbox-cli.exe'
    paths=LIST.read_text().splitlines()
    results=json.loads(LOG.read_text()) if LOG.exists() else {}
    for index,path in enumerate(paths,1):
        if results.get(path, {}).get('Success'):
            continue
        command=subprocess.run([str(cli),'--call','asset_compile',json.dumps({'path':path})],cwd=ROOT,
                               capture_output=True,text=True,timeout=90)
        try:
            response=json.loads(command.stdout)
        except ValueError:
            response={'Success':False,'stdout':command.stdout[-800:],'stderr':command.stderr[-800:]}
        results[path]=response
        LOG.write_text(json.dumps(results,indent=2)+'\n')
        if index%8==0 or not response.get('Success'):
            print(f'{index}/{len(paths)} compiled, success={response.get("Success")}',flush=True)
        if not response.get('Success'):
            raise RuntimeError(f'Native compilation failed for {path}: {response}')
    print(f'Completed {len(paths)} model compiles',flush=True)


if __name__=='__main__':
    main()
