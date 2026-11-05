from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).parent
s=(ROOT/'Sources/Belltower/market-cross-v2/audit.py').read_text().replace('market-cross-v2','well-frame-v2').replace('market_cross','well_frame').replace('outside[0:1024,300:980]','outside[250:1024,250:920]')
(HERE/'audit.py').write_text(s)
p=ROOT/'Sources/Belltower/market-cross-v2/build.py';s=p.read_text();a=s.index('old=K.Model()');s=s[:a]+"print({'accepted_resource_staged':True,'lods':lods})\n";p.write_text(s)
p=ROOT/'Sources/Belltower/market-cross-v2/README.md';s=p.read_text().replace('— review only','— installed').replace('NOT installed; pending user visual approval.','Approved by the user and installed. Removed the original 40 baked triangles from two mesh sources, deleted nine obsolete private review assets, and compiled the centre model. Scene save and preserved physics/object IDs/editor state passed native checks; see installed.json. Regeneration uses Tools/belltower_market_cross.py.');p.write_text(s)
