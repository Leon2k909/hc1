from pathlib import Path
import json,subprocess
r=Path('C:/Users/mimi-/Documents/S&box Projects/hc1');out=Path(__file__).parent
cli='C:/Program Files (x86)/Steam/steamapps/common/sbox/bin/managed/sbox-cli.exe'
def call(tool,args):
    p=subprocess.run([cli,'--call',tool,json.dumps(args)],cwd=r,capture_output=True,text=True,encoding='utf-8',errors='replace')
    if p.returncode:raise RuntimeError(p.stdout+p.stderr)
    print(tool,p.stdout.strip(),flush=True)
def put(path,text):
    call('write_file',{'path':'Assets/'+path,'content':text});call('recompile_asset',{'path':path})
p=r/'Assets/shaders/forestbase_waterfall.shader';s=p.read_text()
s=s.replace('sin(h*.035+g_flTime*3.2+u*23)*2.4','sin(h*.035+g_flTime*3.2+u*23)*8.0').replace('sin(h*.081+g_flTime*6.6-u*49)*1.1','sin(h*.081+g_flTime*6.6-u*49)*3.2')
s=s.replace('sqrt(max(progress,.005))*5.8','sqrt(max(progress,.005))*2.3')
s=s.replace('m.Normal=normalize(m.Normal+tangent*(a.g-b.g)*.20+along*(coarse.b-.5)*.10);','''float3 reliefNormal=normalize(cross(ddx(m.WorldPosition),ddy(m.WorldPosition)));
        if(dot(reliefNormal,m.Normal)<0) reliefNormal=-reliefNormal;
        m.Normal=normalize(lerp(m.Normal,reliefNormal,.7)+tangent*(a.g-b.g)*.20+along*(coarse.b-.5)*.10);''')
put('shaders/forestbase_waterfall.shader',s);(out/'forestbase_waterfall.final.shader').write_text(s)
for k in range(4):
    path=f'materials/forestbase/waterfall_{k}.vmat';p=r/'Assets'/path;put(path,p.read_text().replace('FlowTiling "1"','FlowTiling "2"'))
