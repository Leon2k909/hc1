from pathlib import Path
import sys,json
sys.path.insert(0,'Sources/Belltower/terracotta-pot-v2')
import native
ROOT=Path.cwd();TAG='megascans-lawn-trial-20261105';OUT=ROOT/'output/veridant'/TAG;SOURCE=ROOT/'Sources/Veridant'/TAG
native.OUT=OUT
variant=sys.argv[2] if len(sys.argv)>2 else 'fresh'
assert variant in ('fresh','balanced')
tint='[1.2 2.1 1.4 1]' if variant=='fresh' else '[1.1 1.25 1.05 1]'
if sys.argv[1]=='material':
    code=(SOURCE/'lawn.vmat').read_text().replace('g_vColorTint "[1 1 1 1]"','g_vColorTint "'+tint+'"')
    (SOURCE/('lawn-'+variant+'.vmat')).write_text(code)
    script='''var root=Sandbox.Project.Current.GetRootPath();var source=System.IO.Path.Combine(root,"Sources/Veridant/TAG/lawn-fresh.vmat");var target=System.IO.Path.Combine(root,"Assets/materials/veridant/trials/TAG/lawn-fresh.vmat");if(System.IO.File.Exists(target)) throw new InvalidOperationException("Choose a fresh trial path");System.IO.File.Copy(source,target);Editor.AssetSystem.RegisterFile(target);return new {Target=target};'''.replace('TAG',TAG)
    script=script.replace('lawn-fresh.vmat','lawn-'+variant+'.vmat')
    path=OUT/(variant+'-material.cs.txt');path.write_text(script)
    print(json.dumps(native.script(path,variant+'-material-import')))
    print(json.dumps(native.call('asset_compile',{'path':'materials/veridant/trials/'+TAG+'/lawn-'+variant+'.vmat'},variant+'-material-compile')))
elif sys.argv[1]=='capture':
    config=json.loads((OUT/'capture-request.json').read_text());config['name']='after-'+variant
    (OUT/'capture-request.json').write_text(json.dumps(config))
    code=(OUT/'capture-after.cs.txt').read_text().replace(TAG+'/lawn.vmat',TAG+'/lawn-'+variant+'.vmat')
    path=OUT/('capture-after-'+variant+'.cs.txt');path.write_text(code)
    print(json.dumps(native.script(path,'after-'+variant+'-receipt'),indent=2))
