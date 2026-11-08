from pathlib import Path
ROOT=Path(__file__).absolute().parents[3];p=ROOT/'Tools/riverside_parts.py';s=p.read_text()
s=s.replace('seed=0, name="plank fence" ):','seed=0, name="plank fence", model=False ):')
a=s.index('        for t in np.arange( 0, L, 5.75 ):',s.index('def plank_fence'));b=s.index('        if collide:',a)
block=s[a:b];s=s[:a]+'''        if model:
            if abs(L-500)>0.001 or height!=60 or seed!=1:
                raise ValueError("The approved fence fits only the first 500-inch yard run")
            YARD_FENCES.append([m,tuple(float(q) for q in a+UP*z),math.degrees(math.atan2(dn[1],dn[0]))])
        else:
'''+''.join('    '+l if l.strip() else l for l in block.splitlines(keepends=True))+s[b:]
s=s.replace('+ STORE_STEPS + ROOF_VENTS','+ STORE_STEPS + YARD_FENCES + ROOF_VENTS');p.write_text(s)
