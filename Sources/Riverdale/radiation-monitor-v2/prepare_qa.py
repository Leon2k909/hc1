"""Reuse Riverdale's isolated native renderer without changing the user's scene."""
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
source = (ROOT / 'Sources/Riverdale/editor/capture.cs.txt').read_text()
start = source.index('    var views = new[] {')
end = source.index('    var wanted =', start)
source = source[:start] + '''    var views = new[] {
        (Name: "close", Eye: new Vector3(-965,463,94), Target: new Vector3(-997,470,90), Fov: 48f),
        (Name: "context", Eye: new Vector3(-935,447,90), Target: new Vector3(-999,470,91), Fov: 55f),
    };
''' + source[end:]
source = source.replace('output/riverdale/captures', 'output/riverdale/radiation-monitor-v2/before')
source = source.replace('texture.MarkUsed(1024)', 'texture.MarkUsed(2048)')
source = source.replace('?? 1600', '?? 1280').replace('?? 900', '?? 960')
(HERE / 'capture-before.cs.txt').write_text(source)
(HERE / 'capture-after.cs.txt').write_text(source.replace('radiation-monitor-v2/before', 'radiation-monitor-v2/after'))
install = (ROOT / 'Sources/Riverdale/pool_rules_v2/install.cs.txt').read_text()
install = install.replace('output/riverdale/pool-rules-20261031', 'output/riverdale/radiation-monitor-v2')
install = install.replace('System.IO.File.Copy(source,target,true);', 'var temporary = target + ".arm-installing";\n    System.IO.File.Copy(source,temporary,true);\n    System.IO.File.Move(temporary,target,true);')
(HERE / 'install.cs.txt').write_text(install)
compile = (ROOT / 'Sources/Riverdale/pool_rules_v2/compile.cs.txt').read_text()
mats = ['materials/riverdale/radiation_monitor_v2/rv_arm_' + s + '.vmat' for s in ['shell', 'seal', 'steel', 'panel', 'lcd', 'sign', 'amber', 'green']]
compile = compile.replace('"materials/riverdale/rv_pool_rules_v2.vmat"', ', '.join('"' + m + '"' for m in mats))
(HERE / 'compile.cs.txt').write_text(compile)
