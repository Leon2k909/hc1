from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).parent
t=(ROOT/'Sources/Riverdale/shared-cone-v1/verify.py').read_text().replace('shared-cone-v1','sand-bin-v1').replace('yard_without_cone','yard_without_bin').replace('==166','==38').replace("('cone','detail')","('bin','detail')").replace('TRAFFIC CONE','SAND BIN').replace('removed_old_body_triangles=166','removed_old_body_triangles=38').replace("len(manifest['files'])==3","len(manifest['files'])==6").replace('new_replacement_meshes_or_materials=0','new_replacement_meshes=1')
(HERE/'verify.py').write_text(t)
