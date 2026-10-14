var folder=@"D:\Documents\s&box projects\hc1\forked-shooter-main\output\third-person-sprint\revision";
var names=new[]{"m4a1","aug","kastov74u","rpk","famas","p90","l85a2","uzi","vepr12"};
var available=ResourceLibrary.GetAll<EquipmentResource>().Where(w=>w.WorldModelPrefab.IsValid()).ToArray();
var weapons=names.Select(name=>available.FirstOrDefault(w=>w.ResourceName==name)).Where(w=>w!=null).ToArray();
using var sheet=new Bitmap(1440,weapons.Length*480);
using var close=new Bitmap(960,960);
var reports=new System.Collections.Generic.List<object>();
for(var wi=0;wi<weapons.Length;wi++)
{
    var weapon=weapons[wi];
    cancellationToken.ThrowIfCancellationRequested();
    var scene=new Scene();
    try
    {
        using(scene.Push())
        {
            var body=new GameObject(true,"Sprint weapon fixture").Components.Create<SkinnedModelRenderer>();
            body.Model=Model.Load(Facepunch.MilitaryUniform.HumanModelPath);
            Facepunch.MilitaryUniform.SetModel(body,body.Model,wi%2==0?Facepunch.MilitaryUniformStyle.Standard:Facepunch.MilitaryUniformStyle.Field);
            body.AnimationGraph=AnimationGraph.Load("animgraphs/human_bot.vanmgrph");
            var go=weapon.WorldModelPrefab.Clone(new CloneConfig{StartEnabled=false,Transform=new()});
            foreach(var c in go.GetComponentsInChildren<Component>(true))c.Enabled=c is ModelRenderer||c is Facepunch.WeaponModel;
            go.Enabled=true;
            var gun=go.GetComponentInChildren<Facepunch.WorldModel>();
            gun.ModelRenderer.SetBodyGroup("sight",0);gun.ModelRenderer.SetBodyGroup("muzzle",0);
            var camera=new GameObject(true,"Sprint weapon camera").Components.Create<CameraComponent>();
            camera.FieldOfView=42f;camera.ZNear=1f;camera.BackgroundColor=new Color(.10f,.12f,.15f);
            var light=new GameObject(true,"Sprint weapon light").Components.Create<DirectionalLight>();
            light.WorldRotation=Rotation.From(40f,150f,0f);light.LightColor=Color.White*2f;light.SkyColor=Color.White*.6f;
            var carry=new Facepunch.ThirdPersonSprintPose();
            var mount=Facepunch.MilitaryUniform.WeaponHandOffset(body.Model);
            Transform Bone(string name)=>body.SceneModel.GetBoneWorldTransform(body.Model.Bones.GetBone(name).Index);
            scene.EditorTick(.016f,.016f);
            for(var frame=0;frame<24;frame++)
            {
                body.Set("holdtype",2);body.Set("holdtype_handedness",1);body.Set("b_grounded",1);body.Set("b_twohanded",1);
                body.Set("move_speed",310f);body.Set("move_groundspeed",310f);body.Set("move_x",310f);body.Set("wish_x",310f);body.Set("move_style",2);
                foreach(var name in new[]{"_human_walk_rate_per_inch","_human_run_rate_per_inch","_human_sprint_rate_per_inch"})body.Set(name,1.25f/310f);
                body.SetLookDirection("aim_body",Vector3.Forward,.75f);body.SetLookDirection("aim_head",Vector3.Forward,1f);body.SetLookDirection("aim_eyes",Vector3.Forward,1f);
                body.Set("ik.hand_right.enabled",0);body.Set("ik.hand_left.enabled",0);
                scene.EditorTick((frame+1)*.05f,.05f);
                foreach(var r in body.GetComponentsInChildren<SkinnedModelRenderer>(true))r.SceneModel?.Update(.05f);
                carry.Reset();gun.WorldTransform=Bone("hand_R").WithScale(1f).ToWorld(mount);
                carry.Apply(body,gun,1f,updateBoneObjects:false);
            }
            using var tile=new Bitmap(480,480);
            void Render(Vector3 position,Vector3 target,float fov)
            {
                camera.FieldOfView=fov;camera.WorldPosition=position;camera.WorldRotation=Rotation.LookAt(target-position);
                foreach(var r in go.GetComponentsInChildren<SkinnedModelRenderer>(true)){if(!r.SceneModel.IsValid())continue;r.SceneModel.Transform=r.WorldTransform;r.SceneModel.Update(0f);}
                camera.RenderToBitmap(tile);
            }
            var positions=new[]{new Vector3(15f,106f,61f),new Vector3(105f,-55f,58f),new Vector3(15f,-106f,61f)};
            for(var view=0;view<positions.Length;view++)
            {
                Render(positions[view],new Vector3(5f,0f,38f),42f);
                sheet.DrawBitmap(tile,new Rect(view*480,wi*480,480,480));
            }
            if(wi<2)
            {
                Render(new Vector3(78f,-40f,63f),new Vector3(9f,0f,49f),38f);
                close.DrawBitmap(tile,new Rect(0,wi*480,480,480));
                Render(new Vector3(15f,-82f,63f),new Vector3(9f,0f,49f),38f);
                close.DrawBitmap(tile,new Rect(480,wi*480,480,480));
            }
            reports.Add(new{Row=wi,Weapon=weapon.ResourceName,LeftError=Bone("hand_L").Position.Distance(gun.IkLeftHand.WorldPosition)});
        }
    }
    finally{scene.Destroy();}
    await Task.Delay(10,cancellationToken);
}
var gallery=System.IO.Path.Combine(folder,"weapon-preview.png");
var detail=System.IO.Path.Combine(folder,"m4-aug-close.png");
System.IO.File.WriteAllBytes(gallery,sheet.ToPng());System.IO.File.WriteAllBytes(detail,close.ToPng());
System.IO.File.WriteAllText(System.IO.Path.Combine(folder,"preview.json"),System.Text.Json.JsonSerializer.Serialize(reports,new System.Text.Json.JsonSerializerOptions{WriteIndented=true}));
return new{Gallery=gallery,Detail=detail,Weapons=reports};
