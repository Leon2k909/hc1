from pathlib import Path
folder=Path(__file__).resolve().parent
text=(folder/'preview.cs').read_text()
text=text.replace('structure-timber-v2/review','structure-timber-v2/review-paint')
text=text.replace('lt_cast_iron_v2.vmat','lt_cast_paint_trial.vmat')
text=text.replace('new[]{"before","tuned"}','new[]{"tuned"}')
(folder/'preview-paint.cs').write_text(text,encoding='utf-8')
Path('C:/Users/leon2/AppData/Local/Temp/sbox-cli/9b705a7fa05c489fbc772f40a41b8e93/structure-v2-preview-paint.cs').write_text(text,encoding='utf-8')
