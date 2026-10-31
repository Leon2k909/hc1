"""Prepare one whole-model render for this material-only correction."""
from pathlib import Path
HERE=Path(__file__).parent;ROOT=HERE.parents[2]
s=(HERE/'render_realism.py').read_text()
s=s.replace("OUT=ROOT/'output/asset-improvement-20261030/pump-skid/realism-review'",
            "OUT=ROOT/'output/asset-improvement-20261030/pump-skid/clean-finish-review'")
s=s.replace("OLD=OUT.parent/'revision-01/Assets'","OLD=OUT/'before/Assets'")
s=s.replace("previous=model('previous',OLD);revised=model('revised',ASSETS)",
            "previous=[];revised=model('revised',ASSETS)")
s=s.replace("views=[('main',(4.2,-5.3,3.1),(0,0,.94)),('rear',(-4.2,5.6,3.25),(0,0,.94))]",
            "views=[('main',(4.2,-5.3,3.1),(0,0,.94))]")
s=s.replace("for variant in ('revised','previous'):","for variant in ('revised',):")
s=s.replace("print('Matched previous/revised whole-pump comparisons complete; map sources unchanged.',flush=True)",
            "print('Clean casting finish rendered; geometry and original map unchanged.',flush=True)")
(HERE/'render_clean_finish.py').write_text(s,encoding='utf-8');compile(s,str(HERE/'render_clean_finish.py'),'exec')
wrapper=(HERE/'render_realism_low_impact.py').read_text()
wrapper=wrapper.replace('pump-skid/realism-review','pump-skid/clean-finish-review')
wrapper=wrapper.replace("parent/'render_realism.py'","parent/'render_clean_finish.py'")
(HERE/'render_clean_finish_low_impact.py').write_text(wrapper,encoding='utf-8')
print('Prepared one matched whole-pump view; old material preview retained.')
