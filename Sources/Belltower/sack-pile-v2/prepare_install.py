from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).parent
for name in ('install.cs.txt','delete-old.cs.txt','finish_install.py'):
    s=(ROOT/'Sources/Belltower/bistro-table-v2'/name).read_text().replace('bistro-table-v2','sack-pile-v2').replace('bistro_table.vmdl','sack_pile.vmdl').replace('Bistro tables','Bakery sack piles').replace('tables','piles').replace('Tables','Piles').replace('table','pile').replace('Table','Pile')
    s=s.replace('!=7','!=2').replace('all 7','all 2').replace('Installed=7','Installed=2').replace('3038','168')
    s=s.replace('(modelPath!=pot.ResourcePath)','(modelPath!=pot.ResourcePath && modelPath!="models/maps/belltower/sack-pile-v2/sack_pile_mirrored.vmdl")')
    if name=='finish_install.py':
        s=s.replace("    print('Install:',", """    status=native.call('editor_status');scenes=native.call('list_scenes')['Scenes']
    if not any(r['ResourcePath']=='scenes/maps/belltower/belltower.scene' for r in scenes):
        assert not status['IsPlaying']
        native.call('open_scene',{'path':'scenes/maps/belltower/belltower.scene'})
        native.call('switch_scene',{'scene':status['ActiveScenePath']})
    print('Mirrored sources:',native.script(HERE/'import-mirrored.cs.txt','import-mirrored'),flush=True)
    assert native.call('asset_compile',{'path':'models/maps/belltower/sack-pile-v2/sack_pile_mirrored.vmdl'},'compile-mirrored')['Success']
    print('Install:',""")
    (HERE/name).write_text(s)
s=(ROOT/'Sources/Belltower/wall-lantern-v2/preserve-original.cs.txt').read_text().replace('wall-lantern-v2','sack-pile-v2').replace('retained_original_files','imports').replace('wall-lantern-original/','sack-pile-v2/')
s=s[:s.index('return new{')]+"return new{MirroredSourcesImported=true};\n"
(HERE/'import-mirrored.cs.txt').write_text(s)
