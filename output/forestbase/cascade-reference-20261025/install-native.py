from pathlib import Path
import subprocess,json
r=Path('C:/Users/mimi-/Documents/S&box Projects/hc1');out=Path(__file__).parent
cli='C:/Program Files (x86)/Steam/steamapps/common/sbox/bin/managed/sbox-cli.exe'
def call(name,args):
    p=subprocess.run([cli,'--call',name,json.dumps(args)],cwd=r,capture_output=True,text=True,encoding='utf-8',errors='replace')
    if p.returncode:raise RuntimeError(p.stdout+p.stderr)
    print(name,p.stdout.strip(),flush=True)
    return p.stdout
records=[]
for staged,target in [('forestbase_waterfall.next.shader','shaders/forestbase_waterfall.shader'),('forestbase_basin.next.shader','shaders/forestbase_basin.shader'),
                      ('waterfall_impact.next.vmat','materials/forestbase/waterfall_impact.vmat'),('waterfall_spray.next.vmat','materials/forestbase/waterfall_spray.vmat')]:
    call('write_file',{'path':'Assets/'+target,'content':(out/staged).read_text()})
    records.append({'path':target,'result':call('recompile_asset',{'path':target})})
for p in ('materials/forestbase/waterfall_0.vmat','materials/forestbase/plunge_basin.vmat'):
    records.append({'path':p,'result':call('recompile_asset',{'path':p})})
(out/'native-install.json').write_text(json.dumps(records,indent=2))
