from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).parent
s=(ROOT/'Sources/Belltower/dish-lamp-v2/build.py').read_text()
s=s.replace("e,n0,n1,z=B.CABLES[0];HOOK=(e,(n0+n1)/2,z-12)","HOOK=(-1215.,730.,0.)")
s=s.replace("MAPS={p:L.MAPS[p] for p in ('iron_black','lamp_reflector','lamp_bulb','door_brass')}","MAPS={'canvas_plain':'materials/buildings/canvas_plain.vmat'}")
a=s.index('def shell(');b=s.index('def main():',a)
s=s[:a]+'''def build(lod):
    m=K.Model()
    for k in range(7):
        row,level=k%3,k//3
        centre=np.array((row*22-12+level*6.,0.,level*14+7.))
        # Rounded stuffed canvas, with pinched sides and weight-bearing flat contact areas.
        part=K.Model();p=B.Place((0,0,0),0)
        F.sack(part,p,centre,size=(20,28,14),seed=k+3)
        # Simplify source surface tessellation only in the far LOD by skipping separate seam hardware.
        for paint,faces in part.polygons.items():
            for i,(points,normal) in enumerate(faces):
                m.polygon(paint,points,normal,uv=part.polygon_uvs.get((paint,i)),normals=part.polygon_normals.get((paint,i)))
        if lod<2:
            # Rolled end seam and paired rows of stitches at the sewn mouth.
            points=[centre+np.array((x,12.2,1.2-.018*x*x)) for x in np.linspace(-7.4,7.4,17)]
            L.C.tube(m,points,.15,'canvas_plain',sides=6)
            if lod==0:
                for x in np.linspace(-6.8,6.8,15):
                    q=centre+np.array((x,12.35,1.25-.018*x*x))
                    D.rod(m,q+(-.1,0,-.23),q+(.1,0,.23),.035,'canvas_plain',sides=4)
    D.configure(m);m.material_overrides.update(MAPS);return m

'''+s[b:]
s=s.replace('D.dish_lamp(old,HOOK)','B.sacks(old,HOOK[:2],0,7)')
s=s.replace('_(iron_black|lamp_bulb|lamp_reflector)', '_(canvas_plain)')
s=s.replace("('iron_black','lamp_bulb','lamp_reflector')","('canvas_plain',)")
s=s.replace('dish-lamp-v2','sack-pile-v2')
s=s.replace('world+np.array((30.,50.,-24.))','world+np.array((75.,90.,65.))').replace('world+np.array((0,0,-6.))','world+np.array((0,0,20.))')
# Replace the template camera signature with this pile view.
s=s.replace("s=s.replace('position=(443", "s=s.replace('position=(443")
s=s.replace('wall_lantern.vmdl','sack_pile.vmdl')
s=s.replace("(MODEL/'sack_pile.vmdl').write_text(L.modeldoc())","(MODEL/'sack_pile.vmdl').write_text(L.modeldoc())")
s=s.replace("s=s.replace('new Vector3(475", "s=s.replace('new Vector3(475")
# The review template's model path is supplied by its helper replacement.
s=s.replace("s=s.replace('0,180,0','0,0,0')", "s=s.replace('0,180,0','0,0,0')")
(HERE/'build.py').write_text(s)
