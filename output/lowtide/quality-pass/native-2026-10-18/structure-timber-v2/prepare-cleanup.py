from pathlib import Path
folder=Path(__file__).resolve().parent
exchange=Path('C:/Users/leon2/AppData/Local/Temp/sbox-cli/9b705a7fa05c489fbc772f40a41b8e93')
text=(folder.parent/'warehouse-floor-current/cleanup-bake.cs').read_text().replace('warehouse-floor-current','structure-timber-v2').replace('PreservedStableV4','PreservedStableV5')
(folder/'cleanup-bake.cs').write_text(text,encoding='utf-8')
(exchange/'structure-v2-cleanup-bake.cs').write_text(text,encoding='utf-8')
(exchange/'structure-v2-retire-trial.cs').write_bytes((folder/'retire-trial.cs').read_bytes())
restore=(folder.parent/'structure-response/restore-map.cs').read_text().replace('riverdale','lowtide')
(folder/'restore-map.cs').write_text(restore,encoding='utf-8')
(exchange/'structure-v2-restore-map.cs').write_text(restore,encoding='utf-8')
