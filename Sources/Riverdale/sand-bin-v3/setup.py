from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).parent;prior=ROOT/'Sources/Riverdale/sand-bin-v2'
t=(prior/'model.py').read_text().replace('sand-bin-v2','sand-bin-v3')
start=t.index(' # Tapered moulded');end=t.index(' Y.printed',start)
t=t[:start]+''' # Three structural feet leave two real, open forklift channels below the vessel.
 for x in (-13.,0.,13.):box((x,0,1.65),(5.,19.4,3.3),b=.65)
 loft([ring(14.6,9.2,1.5,3.1),ring(15.1,9.7,1.8,3.6),ring(15.1,9.7,1.8,4.2),ring(15.5,10.,2.,5.3),ring(16.6,10.6,2.4,19.8,.13),ring(17.,11.,2.5,23.8,.16),ring(17.,11.,2.5,24.8,.16)],'rv_yd_bin')
 # A positive shoulder and separately formed rain skirt define the lid/body interface.
 loft([ring(17.05,11.05,2.5,24.7,.16),ring(17.35,11.35,2.7,25.1,.16),ring(17.35,11.35,2.7,25.5,.16)],'rv_yd_bin')
 loft([ring(17.45,11.45,2.7,25.45,.16),ring(17.45,11.45,2.7,25.65,.16)],'rv_black')
 # Thick double-wall lid with a rolled perimeter, broad inset crown and drainage fall.
 loft([ring(17.6,11.8,2.7,25.65,.16),ring(18.,12.3,3.,26.05,.16),ring(18.,12.3,3.,27.35,.16),ring(17.8,12.1,2.9,27.8,.16),ring(17.1,11.4,2.5,28.1,.16),ring(15.7,10.,1.8,28.1,.16),ring(15.25,9.55,1.6,27.7,.16)],'rv_yd_bin')
 # Wide rounded stiffening forms in the lid, instead of the previous thin sticks.
 Yaxis=K.normalise(F-Z*.16);LZ=K.normalise(np.cross(X,Yaxis))
 for x in (-9.5,9.5):
  box((x,0,27.95),(2.5,17.4,.65),b=.30,axes=(X,Yaxis,LZ))
 # Formed side panels and carrying grips. A hollow grip has an actual open underside.
 for sg in (-1,1):
  side=X*sg
  box((sg*16.25,0,13.),(.65,13.,12.),b=.30)
  for y in (-5.5,5.5):box((sg*16.8,y,20.15),(1.3,1.2,2.8),b=.45)
  box((sg*17.1,0,21.25),(1.2,11.9,1.1),b=.48)
  # Recessed dark shadow behind the handle, without covering its clear hand opening.
  box((sg*16.15,0,20.),(.12,9.,1.8),'rv_black',.25)
 # A thicker front sign mounting island blends into the tapered shell.
 box((0,10.7,13.8),(23.8,.65,10.8),b=.28)
 # Proper rear hinge leaves, interleaved knuckles, pin heads and fixing heads.
 for x in (-10.5,10.5):
  box((x,-11.35,25.4),(4.3,.24,3.4),'rv_zinc',.10)
  for dx in (-1.5,-.5,.5,1.5):
   G.lathe_axis(m,P(x+dx-.43,-11.9,29.1),X,[(0,0),(.48,0),(.48,.86),(0,.86)],'rv_zinc',sides=32)
  G.lathe_axis(m,P(x-2.15,-11.9,29.1),X,[(0,0),(.22,0),(.22,4.3),(0,4.3)],'rv_zinc',sides=24)
  for dx in (-1.4,1.4):
   G.lathe_axis(m,P(x+dx,-11.51,25.1),-F,[(0,0),(.18,0),(.18,.08),(0,.08)],'rv_zinc',sides=16)
 # Deep front handle surround, paired mounting ears and a bent steel bail grip.
 box((0,11.45,22.2),(9.5,.28,3.4),'rv_black',.55)
 for x in (-3.65,3.65):box((x,12.1,23.1),(.65,1.1,1.45),'rv_zinc',.15)
 D.tube(m,[P(-3.65,12.1,23.2),P(-3.65,12.9,22.1),P(-3.15,13.2,21.7),P(3.15,13.2,21.7),P(3.65,12.9,22.1),P(3.65,12.1,23.2)],.20,'rv_zinc',sides=16)
 # Folded hasp at the lid edge; the eye is a true open annulus, not a black dot.
 box((0,12.36,24.9),(1.55,.20,2.9),'rv_zinc',.09)
 G.lathe_axis(m,P(0,12.5,24.2),F,[(.18,0),(.38,0),(.38,.55),(.18,.55),(.18,0)],'rv_zinc',sides=32)
 # Small drain bung seated in a moulded boss on the side of the vessel.
 G.lathe_axis(m,P(15.55,-6.5,6.1),X,[(0,0),(.83,0),(.83,.45),(0,.45)],'rv_black',sides=32)
 G.lathe_axis(m,P(16.,-6.5,6.1),X,[(0,0),(.55,0),(.55,.25),(0,.25)],'rv_zinc',sides=6)
'''+t[end:]
(HERE/'model.py').write_text(t)
for name in ('surfaces.py','build.py','verify.py'):
 s=(prior/name).read_text().replace('sand-bin-v2','sand-bin-v3');(HERE/name).write_text(s)
# Compare the last rejected revision with this structural rebuild.
s=(prior/'prepare_review.py').read_text().replace('sand-bin-v2','sand-bin-v3').replace('sand-bin-v1/sand_bin.vmdl','sand-bin-v2/sand_bin.vmdl');(HERE/'prepare_review.py').write_text(s)
