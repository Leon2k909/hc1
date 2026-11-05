from pathlib import Path
root=Path(__file__).resolve().parents[3]
here=Path(__file__).resolve().parent
s=(root/'Sources/Spillway/waterline-fix-v1/native.py').read_text().replace('output/spillway/waterline-fix-v1','output/spillway/service-cabinet-v1')
(here/'native.py').write_text(s)
