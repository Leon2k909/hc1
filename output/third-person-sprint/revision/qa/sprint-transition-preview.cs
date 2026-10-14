var folder = @"D:\Documents\s&box projects\hc1\forked-shooter-main\output\third-person-sprint\revision";
System.IO.Directory.CreateDirectory(folder);
var captures=new[]{11,17,23,29};
var reports=new System.Collections.Generic.List<object>();
foreach(var weapon in Facepunch.LightweightCombatBot.WeaponPool().Where(w=>new[]{"m4a1","aug"}.Contains(w.ResourceName)))
{
    using var sheet=new Bitmap(1440,captures.Length*480);
    var scene=new Scene();
    try
    {
        using(scene.Push())
        {
            var body=new GameObject(true,"Sprint cycle fixture").Components.Create<SkinnedModelRenderer>();
            body.Model=Model.Load(Facepunch.MilitaryUniform.HumanModelPath);
            Facepunch.MilitaryUniform.SetModel(body,body.Model,Facepunch.MilitaryUniformStyle.Standard);
            body.AnimationGraph=AnimationGraph.Load("animgraphs/human_bot.vanmgrph");
            var go=weapon.WorldModelPrefab.Clone(new CloneConfig{StartEnabled=false,Transform=new()});
            foreach(var c in go.GetComponentsInChildren<Component>(true))c.Enabled=c is ModelRenderer||c is Facepunch.WeaponModel;
            go.Enabled=true;
            var gun=go.GetComponentInChildren<Facepunch.WorldModel>();
            gun.ModelRenderer.SetBodyGroup("sight",0);gun.ModelRenderer.SetBodyGroup("muzzle",0);
            var camera=new GameObject(true,"Sprint cycle camera").Components.Create<CameraComponent>();
            camera.FieldOfView=42f;camera.ZNear=1f;camera.BackgroundColor=new Color(.10f,.12f,.15f);
            var light=new GameObject(true,"Sprint cycle light").Components.Create<DirectionalLight>();
            light.WorldRotation=Rotation.From(40f,150f,0f);light.LightColor=Color.White*2f;light.SkyColor=Color.White*.6f;
            var carry=new Facepunch.ThirdPersonSprintPose();var shape=new Facepunch.BotWeaponPose();
            var mount=Facepunch.MilitaryUniform.WeaponHandOffset(body.Model);
            Transform Bone(string name)=>body.SceneModel.GetBoneWorldTransform(body.Model.Bones.GetBone(name).Index);
            scene.EditorTick(.016f,.016f);
            for(var frame=0;frame<=captures.Last();frame++)
            {
                cancellationToken.ThrowIfCancellationRequested();
                body.Set("holdtype",2);body.Set("holdtype_handedness",1);body.Set("b_grounded",1);body.Set("b_twohanded",1);
                body.Set("move_speed",310f);body.Set("move_groundspeed",310f);body.Set("move_x",310f);body.Set("wish_x",310f);body.Set("move_style",2);
                foreach(var name in new[]{"_human_walk_rate_per_inch","_human_run_rate_per_inch","_human_sprint_rate_per_inch"})body.Set(name,1.25f/310f);
                body.SetLookDirection("aim_body",Vector3.Forward,.75f);body.SetLookDirection("aim_head",Vector3.Forward,1f);body.SetLookDirection("aim_eyes",Vector3.Forward,1f);
                body.Set("ik.hand_right.enabled",0);body.Set("ik.hand_left.enabled",0);
                scene.EditorTick((frame+1)*.05f,.05f);
                foreach(var r in body.GetComponentsInChildren<SkinnedModelRenderer>(true))r.SceneModel?.Update(.05f);
                carry.Reset();gun.WorldTransform=Bone("hand_R").WithScale(1f).ToWorld(mount);
                var blend=frame<12?.25f:frame<18?.5f:frame<24?.75f:1f;
                carry.Apply(body,gun,blend,updateBoneObjects:false);
                var row=Array.IndexOf(captures,frame);if(row<0)continue;
                var stock=shape.ButtstockContact(gun);
                reports.Add(new{Weapon=weapon.ResourceName,Frame=frame,Blend=blend,Gun=gun.WorldTransform,Stock=gun.WorldTransform.PointToWorld(stock),LeftError=Bone("hand_L").Position.Distance(gun.IkLeftHand.WorldPosition),RightIndex=gun.WorldTransform.PointToLocal(Bone("finger_index_0_R").Position)});
                using var tile=new Bitmap(480,480);
                var positions=new[]{new Vector3(15f,106f,61f),new Vector3(105f,-55f,58f),new Vector3(15f,-106f,61f)};
                for(var view=0;view<positions.Length;view++)
                {
                    camera.WorldPosition=positions[view];camera.WorldRotation=Rotation.LookAt(new Vector3(5f,0f,38f)-camera.WorldPosition);
                    foreach(var r in go.GetComponentsInChildren<SkinnedModelRenderer>(true)){if(!r.SceneModel.IsValid())continue;r.SceneModel.Transform=r.WorldTransform;r.SceneModel.Update(0f);}
                    camera.RenderToBitmap(tile);sheet.DrawBitmap(tile,new Rect(view*480,row*480,480,480));
                }
            }
        }
    }
    finally{scene.Destroy();}
    System.IO.File.WriteAllBytes(System.IO.Path.Combine(folder,weapon.ResourceName+"-transition.png"),sheet.ToPng());
    await Task.Delay(10,cancellationToken);
}
System.IO.File.WriteAllText(System.IO.Path.Combine(folder,"transition.json"),System.Text.Json.JsonSerializer.Serialize(reports,new System.Text.Json.JsonSerializerOptions{WriteIndented=true}));
return reports;
