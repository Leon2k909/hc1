from pathlib import Path
HERE=Path(__file__).parent
s=(HERE/'render_low_impact.py').read_text()
s=s.replace("'output/asset-improvement-20261030/pump-skid'","'output/asset-improvement-20261030/pump-skid/realism-review'")
s=s.replace("parent/'render.py'","parent/'render_realism.py'")
s=s.replace("if '--after-only' in sys.argv:command+=['--','--after-only']", "if '--after-only' in sys.argv:command+=['--','--after-only']\nif '--draft' in sys.argv:command+=['--','--draft']")
s=s.replace("if '--draft' in sys.argv:command+=['--','--draft']", "if '--draft' in sys.argv:command+=['--','--draft']\nif '--surface-review' in sys.argv:command+=['--','--surface-review']")
s=s.replace("if '--surface-review' in sys.argv:command+=['--','--surface-review']", "if '--surface-review' in sys.argv:command+=['--','--surface-review']\nif '--surface-first' in sys.argv:command+=['--','--surface-first']")
(HERE/'render_realism_low_impact.py').write_text(s,encoding='utf-8')
(HERE.parents[2]/'output/asset-improvement-20261030/pump-skid/realism-review').mkdir(parents=True,exist_ok=True)
compile(s,str(HERE/'render_realism_low_impact.py'),'exec')
print('Prepared a single idle-priority, two-thread CPU comparison render.')
