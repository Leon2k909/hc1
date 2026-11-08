from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2]
s=(ROOT/'Sources/Orion/mount-lamps-v1/build.py').read_text().replace('mount-lamps-v1','mount-pedestals-v1').replace('import lamp as G','import pedestal as G')
s=s.replace("('lamp',G.build)","('pedestal',G.build)")
s=s.replace('m=draw(K.Model(),G.CENTRES[0]);R.configure(m);','m=draw(K.Model(),G.CENTRES[0]);import orion_mount_lamps as L;L.build(m,(e,n,z+46));R.configure(m);')
a=s.index("s=(ROOT/'Sources/Orion/yard-lamp-v1/capture.cs.txt')");b=s.index("(HERE/'capture.cs.txt').write_text(s)",a)
s=s[:a]+'''s=(ROOT/'Sources/ReefHall/office-desk-v1/capture.cs.txt').read_text().replace('Sources/ReefHall/office-desk-v1','Sources/Orion/mount-pedestals-v1').replace('models/maps/reefhall/office-desk-v1/','models/maps/orion/mount-pedestals-v1/').replace('"before","desk"','"before","pedestal"').replace('W(95,-125,90)','W(60,-80,58)').replace('W(0,0,26)','W(0,0,24)').replace('FieldOfView=42','FieldOfView=38')
'''+s[b:]
s=s.replace('new Vector3({e+30}f,{n-40}f,{z+20}f)','new Vector3({e+50}f,{n-75}f,{z+58}f)').replace('new Vector3({e}f,{n}f,{z-12}f)','new Vector3({e}f,{n}f,{z+23}f)')
s=s.replace('new Vector3({e-85}f,{n-130}f,{z+65}f)','new Vector3({e-85}f,{n-130}f,{z+100}f)').replace('new Vector3({e+40}f,{n+50}f,{z-35}f)','new Vector3({e+40}f,{n+50}f,{z+15}f)')
s=s.replace("('before','lamp','pad_preview')","('before','pedestal','pad_preview')")
(HERE/'build.py').write_text(s)
