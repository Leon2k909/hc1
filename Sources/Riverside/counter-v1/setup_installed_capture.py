from pathlib import Path
HERE=Path(__file__).parent
s=(HERE/'runtime-review.cs.txt').read_text(encoding='utf-8')
start=s.index('var without=');end=s.index('var gameplay=',start)
s=s[:start]+'''if(original.IsError || original.MeshInfo.LodCount!=7)throw new Exception("Installed counter did not compile with all LOD groups");
'''+s[end:]
start=s.index('  item=new GameObject(');end=s.index('  foreach(var variant',start);s=s[:start]+s[end:]
s=s.replace('new[]{"before","after"}','new[]{"installed"}').replace('   store.Model=variant=="after"?without:original;item.Enabled=variant=="after";\n','')
s=s.replace('PreviewOnly=true','Installed=true,NoRuntimeModelSubstitution=true').replace('Candidate=candidate.MeshInfo,StoreWithout=without.MeshInfo,PublicStore=original.MeshInfo','PublicStore=original.MeshInfo')
s=s.replace('"runtime-review.json"','"installed-runtime.json"').replace('report.PreviewOnly','report.Installed')
(HERE/'runtime-installed.cs.txt').write_text(s,encoding='utf-8')
c=(HERE/'capture.py').read_text(encoding='utf-8').replace("'runtime-review.cs.txt'","'runtime-installed.cs.txt'").replace("'state-restored.json'","'installed-state-restored.json'")
(HERE/'capture_installed.py').write_text(c,encoding='utf-8')
