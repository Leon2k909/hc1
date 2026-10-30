from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
s=(ROOT/'Sources/Collider/equipment-case-trial-v1/render.py').read_text()
s=s.replace("OUT=ROOT/'output/asset-improvement-20261029/equipment-case'","OUT=ROOT/'output/asset-improvement-20261029/monitor'")
s=s.replace("RESOURCE='models/props/collider/equipment-case-trial-v1'","RESOURCE='models/props/collider/monitor-trial-v1'")
s=s.replace('output/collider-case-accepted-20261029/retired-before-resources','output/collider-monitor-accepted-20261029/retired-before-resources')
s=s.replace('scene.cycles.samples=48','scene.cycles.samples=32')
s=s.replace("location=(0,0,-.005)","location=(0,0,-.26)")
s=s.replace("views=[('main',(3.5,-4.6,3.3),(0,0,.85)),('detail',(2.25,-3.5,1.85),(.35,-.55,.95))]",
    "views=[('main',(3.3,-4.8,2.9),(0,.1,.86)),('rear',(3.3,4.8,2.9),(0,.1,.86))]")
s=s.replace("data.lens=54. if view=='main' else 67.","data.lens=50.")
s=s.replace("    for variant,objects in (('before',before),('after',after)):\n",
    """    for variant,objects in (('before',before),('after',after)):
        if variant=='before' and '--after-only' in sys.argv:
            previous=json.loads((OUT/'render-report.json').read_text())
            assert all(previous[k]==report[k] for k in ('renderer','samples','viewTransform','exposure'))
            cached=next(item for item in previous['images'] if item['variant']==variant and item['view']==view)
            assert cached['eyeMetres']==list(eye) and cached['targetMetres']==list(target) and cached['lens']==data.lens
            assert cached['width']==scene.render.resolution_x and cached['height']==scene.render.resolution_y
            assert hashlib.sha256((OUT/cached['file']).read_bytes()).hexdigest()==cached['sha256']
            report['images'].append(cached)
            continue
""")
(Path(__file__).parent/'render.py').write_text(s)
print('Prepared matched front-quarter monitor renders.')
