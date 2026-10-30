from pathlib import Path
import subprocess,json,shutil
r=Path('C:/Users/mimi-/Documents/S&box Projects/hc1');out=Path(__file__).parent
cli='C:/Program Files (x86)/Steam/steamapps/common/sbox/bin/managed/sbox-cli.exe'
def call(name,args):
    p=subprocess.run([cli,'--call',name,json.dumps(args)],cwd=r,capture_output=True,text=True,encoding='utf-8',errors='replace')
    if p.returncode:raise RuntimeError(p.stdout+p.stderr)
    print(name,p.stdout.strip(),flush=True)
def write(path,s):
    call('write_file',{'path':'Assets/'+path,'content':s});call('recompile_asset',{'path':path})
fall=(r/'Assets/shaders/forestbase_waterfall.shader').read_text()
fall=fall.replace('saturate(.42+filaments*.40+core*.18+progress*.10)','saturate(.18+filaments*.65+core*.12+progress*.08)')
write('shaders/forestbase_waterfall.shader',fall)
mist=(out/'forestbase_mist.shader.before').read_text()
mist=mist.replace('PixelInput MainVs(VertexInput i) { return FinalizeVertex(ProcessVertex(i)); }','''PixelInput MainVs(VertexInput i)
    {
        PixelInput o=ProcessVertex(i);
        // Put low spray in front of the water body instead of behind it.
        float foot=1-smoothstep(20,240,o.vPositionWs.z);
        o.vPositionWs.x-=150*foot;
        o.vPositionPs=Position3WsToPs(o.vPositionWs);
        return FinalizeVertex(o);
    }''')
mist=mist.replace('m.Opacity=1-exp(-density*1.8);','''m.Opacity=(1-exp(-density*1.8))*(.15+.85*(1-smoothstep(20,270,m.WorldPosition.z)));''')
write('shaders/forestbase_mist.shader',mist)
for k in range(4):
    path=f'materials/forestbase/waterfall_{k}.vmat';p=r/'Assets'/path
    if not (out/(f'waterfall_{k}.before.vmat')).exists():shutil.copy2(p,out/(f'waterfall_{k}.before.vmat'))
    write(path,p.read_text().replace('FlowTiling "4"','FlowTiling "1"'))
for path in ('materials/forestbase/waterfall_spray.vmat','materials/forestbase/waterfall_impact.vmat'):
    call('recompile_asset',{'path':path})
