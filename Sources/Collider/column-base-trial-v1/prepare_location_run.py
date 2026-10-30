from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).parent
OUT=ROOT/'output/asset-improvement-20261030/column-base/location-review';OUT.mkdir(parents=True,exist_ok=True)
s=(HERE/'render_low_impact.py').read_text()
s=s.replace('output/asset-improvement-20261030/column-base','output/asset-improvement-20261030/column-base/location-review')
s=s.replace("parent/'render.py'","parent/'render_location.py'")
(HERE/'render_location_low_impact.py').write_text(s)
print('Prepared single low-priority CPU location render.')
