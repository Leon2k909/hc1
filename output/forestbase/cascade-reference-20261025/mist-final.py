from pathlib import Path
import subprocess,json
r=Path('C:/Users/mimi-/Documents/S&box Projects/hc1');out=Path(__file__).parent
p=r/'Assets/shaders/forestbase_mist.shader';s=p.read_text()
s=s.replace('float basin=length((float2(-m.WorldPosition.y,m.WorldPosition.x)-float2(430,3370))/float2(530,440));',
'''// Keep the authored basin mask while moving the spray toward the viewer.
        float originalNorth=m.WorldPosition.x+150*(1-smoothstep(20,240,m.WorldPosition.z));
        float basin=length((float2(-m.WorldPosition.y,originalNorth)-float2(430,3370))/float2(530,440));''')
s=s.replace('m.Emission=float3(.30,.35,.38);','m.Emission=float3(.42,.46,.47);')
cli='C:/Program Files (x86)/Steam/steamapps/common/sbox/bin/managed/sbox-cli.exe'
for tool,args in [('write_file',{'path':'Assets/shaders/forestbase_mist.shader','content':s}),('recompile_asset',{'path':'shaders/forestbase_mist.shader'}),('recompile_asset',{'path':'materials/forestbase/waterfall_impact.vmat'}),('recompile_asset',{'path':'materials/forestbase/waterfall_spray.vmat'})]:
    result=subprocess.run([cli,'--call',tool,json.dumps(args)],cwd=r,capture_output=True,text=True,encoding='utf-8',errors='replace')
    assert result.returncode==0,result.stdout+result.stderr
    print(tool,result.stdout.strip(),flush=True)
(out/'forestbase_mist.final.shader').write_text(s)
