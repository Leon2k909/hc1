from pathlib import Path
from native import ROOT,OUT
here=Path(__file__).parent
t=(ROOT/'Sources/Riverdale/shared-reel-v1/verify.py').read_text().replace('shared-reel-v1','shared-cone-v1').replace('yard_without_reel','yard_without_cone').replace('==300','==166').replace('==176','==0').replace("('reel','detail')","('cone','detail')").replace('CABLE REEL','TRAFFIC CONE').replace('removed_old_body_triangles=300','removed_old_body_triangles=166').replace('preserved_cable_tail_triangles=176','preserved_cable_tail_triangles=0')
(here/'verify.py').write_text(t)
s=here/'runtime_review.cs.txt';t=s.read_text();anchor=' var report=new { ActualPlayMode='
addition=''' var installedReel=scene.GetAllComponents<ModelRenderer>().Single(r=>r.GameObject.Name=="Riverdale north-lane cable reel");
 if(installedReel.Model?.ResourcePath!="models/maps/railhead/cable-drum-v1/cable_drum.vmdl"||installedReel.Model.IsError)throw new Exception("Installed reel failed verification");
 camera.WorldPosition=new Vector3(2345,-145,65);camera.WorldRotation=Rotation.LookAt(new Vector3(2420,-60,20)-camera.WorldPosition);camera.FieldOfView=40;camera.CustomSize=new Vector2(1200,900);
 using(var installedShot=new Bitmap(1200,900)) {
  for(int frame=0;frame<180;frame++){CheckRuntime();camera.RenderToBitmap(installedShot,false);await Task.Delay(20,cancellationToken);}
  System.IO.File.WriteAllBytes(System.IO.Path.Combine(folder,"installed-reel.png"),installedShot.ToPng());
 }
'''
assert anchor in t;t=t.replace(anchor,addition+anchor);s.write_text(t)
