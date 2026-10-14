// Native s&box regression: deferred renderer transforms must not add camera movement to the torso or sleeves.
// Run through run_csharp. Uses isolated scenes; leaves the user's scene, play state and equipment untouched.
var project = Project.Current.GetRootPath();
var folder = System.IO.Path.Combine(project, "output", "viewmodel-jump-clipping");
System.IO.Directory.CreateDirectory(folder);
var prefabPaths = System.IO.Directory.GetFiles(System.IO.Path.Combine(project,"Assets","Weapons"),"vm_*.prefab",System.IO.SearchOption.AllDirectories)
    .Select(path=>System.IO.Path.GetRelativePath(System.IO.Path.Combine(project,"Assets"),path).Replace('\\','/').ToLowerInvariant()).OrderBy(path=>path).ToArray();
var flags = System.Reflection.BindingFlags.NonPublic | System.Reflection.BindingFlags.Instance;
var dress = typeof(Facepunch.ViewModelClothing).GetMethod("Dress",flags);
var apply = typeof(Facepunch.ViewModelClothing).GetMethod("Apply",flags);
var retarget = typeof(Facepunch.SwbArmsRetarget).GetMethod("Apply",flags);
var rows = new System.Collections.Generic.List<object>();
var failures = new System.Collections.Generic.List<object>();
var captures = new System.Collections.Generic.List<string>();
var skipped = new System.Collections.Generic.List<string>();
var copiedNames = new[] { "clavicle_L", "clavicle_R", "arm_upper_L", "arm_upper_R", "arm_lower_L", "arm_lower_R", "hand_L", "hand_R", "finger_index_0_L", "finger_index_0_R" };
var positions = new[] { Vector3.Zero, new Vector3(0,0,10), new Vector3(0,0,25), new Vector3(0,0,8), Vector3.Zero, new Vector3(600,-1000,100), new Vector3(603,-1002,110), Vector3.Zero };
foreach (var prefabPath in prefabPaths)
{
    cancellationToken.ThrowIfCancellationRequested();
    var scene = new Scene();
    try
    {
        using var scope = scene.Push();
        var prefab = ResourceLibrary.Get<PrefabFile>(prefabPath);
        if (prefab is null) { failures.Add(new { Prefab=prefabPath, Error="Missing prefab resource" }); continue; }
        var root = SceneUtility.GetPrefabScene(prefab).Clone(new CloneConfig { StartEnabled=false, Transform=global::Transform.Zero });
        var vm = root.Components.Get<Facepunch.ViewModel>(FindMode.EverythingInSelfAndDescendants);
        var arms = vm?.Arms;
        var gun = vm?.ModelRenderer;
        if (!arms.IsValid() || !gun.IsValid()) { skipped.Add(prefabPath+": legacy prefab without the shared clothing component"); continue; }
        foreach (var component in root.Components.GetAll<Component>(FindMode.EverythingInSelfAndDescendants))
            component.Enabled = component is ModelRenderer;
        foreach (var renderer in root.Components.GetAll<ModelRenderer>(FindMode.EverythingInSelfAndDescendants))
        {
            renderer.RenderOptions.Game = true;
            renderer.RenderOptions.Overlay = false;
        }
        var bodyObject = new GameObject(true,"Outfit source");
        bodyObject.WorldPosition = new Vector3(0,0,-5000);
        var body = bodyObject.AddComponent<SkinnedModelRenderer>(false);
        body.Model = Model.Load(Facepunch.MilitaryUniform.HumanModelPath);
        var uniform = bodyObject.AddComponent<Facepunch.MilitaryUniform>(false);
        var source = SceneUtility.GetPrefabScene(ResourceLibrary.Get<PrefabFile>("prefabs/player/player.prefab"))
            .Components.Get<Facepunch.MilitaryUniform>(FindMode.EverythingInSelfAndDescendants);
        uniform.Pieces = source.Pieces.ToList();
        uniform.FieldPieces = source.FieldPieces.ToList();
        uniform.TacticalPieces = source.TacticalPieces.ToList();
        uniform.MilitiaPieces = source.MilitiaPieces.ToList();
        root.Enabled = true;
        var clothing = root.AddComponent<Facepunch.ViewModelClothing>();
        clothing.Arms = arms;
        clothing.Body = body;
        clothing.Enabled = false;
        var camera = new GameObject(true,"Eye").AddComponent<CameraComponent>();
        camera.IsMainCamera = false;
        camera.FieldOfView = 85;
        camera.ZNear = 1;
        camera.BackgroundColor = new Color(.3f,.35f,.4f);
        var light = new GameObject(true,"Light").AddComponent<DirectionalLight>();
        light.WorldRotation = Rotation.From(new Angles(50,30,0));
        light.LightColor = Color.White * 2;
        light.SkyColor = Color.White * .8f;
        scene.EditorTick(.01f,.01f);
        var model = gun.SceneModel;
        if (!model.IsValid() || !arms.SceneModel.IsValid()) throw new Exception("No render skeleton");
        var armPoser = root.Components.Get<Facepunch.SwbArmsRetarget>(FindMode.EverythingInSelfAndDescendants);
        foreach (var style in Enum.GetValues<Facepunch.MilitaryUniformStyle>())
        {
            uniform.Style = style;
            dress.Invoke(clothing,new object[] { uniform });
            scene.EditorTick(.01f,.01f);
            scene.EditorTick(.01f,.01f);
            var skin = arms.GameObject.GetComponentsInChildren<SkinnedModelRenderer>(true).First(r=>r.GameObject.Name=="Clothing");
            var layers = arms.GameObject.GetComponentsInChildren<SkinnedModelRenderer>(true).Where(r=>r!=arms && r.Enabled && r.Model is not null && r.SceneModel.IsValid()).ToArray();
            float eyeError=0, armError=0, garmentError=0, boneAngleError=0;
            string worst="";
            int samples=0;
            foreach (var phase in new[] { "hip", "ads", "reload", "sprint", "jump" })
            {
                root.WorldTransform=global::Transform.Zero;
                camera.WorldTransform=global::Transform.Zero;
                gun.SceneModel.Transform=gun.WorldTransform;
                arms.SceneModel.Transform=arms.WorldTransform;
                arms.SceneModel.ClearBoneOverrides();
                Facepunch.AnimBools.SetBool(gun,"b_deploy_skip",true);
                Facepunch.AnimBools.SetBool(gun,"b_sprint",phase=="sprint");
                Facepunch.AnimBools.SetBool(gun,"b_reload",phase=="reload");
                Facepunch.AnimBools.SetBool(gun,"b_jump",phase=="jump");
                Facepunch.AnimBools.SetBool(gun,"b_grounded",phase!="jump");
                model.SetAnimParameter("ironsights_weight",phase=="ads" ? 1f : 0f);
                model.SetAnimParameter("ironsights",phase=="ads" ? 1 : 0);
                for (int step=0;step<45;step++) model.Update(1f/60f);
                if (armPoser.IsValid()) retarget.Invoke(armPoser,null);
                else if(arms!=gun) arms.SceneModel.MergeBones(model);
                // Freeze the sampled animation pose. Render synchronization must not advance the graph between
                // taking its pose and checking the clothing derived from it.
                var fixedPose=Enumerable.Range(0,arms.Model.BoneCount).Select(i=>arms.SceneModel.Transform.ToLocal(arms.SceneModel.GetBoneWorldTransform(i))).ToArray();
                for(int bone=0;bone<fixedPose.Length;bone++) arms.SceneModel.SetBoneOverride(bone,fixedPose[bone]);
                apply.Invoke(clothing,new object[] { camera.WorldTransform });
                foreach(var layer in layers) layer.SceneModel.Update(0);
                var reference=layers.Select(layer=>Enumerable.Range(0,layer.Model.BoneCount).Select(i=>camera.WorldTransform.ToLocal(layer.SceneModel.GetBoneWorldTransform(i))).ToArray()).ToArray();
                foreach (var order in new[] { "deferred", "arms-first", "clothing-first", "current" })
                {
                    foreach (var position in positions)
                    {
                        cancellationToken.ThrowIfCancellationRequested();
                        var rotation = position.x>0 ? Rotation.From(new Angles(-20,45,15)) : Rotation.Identity;
                        root.WorldTransform = new Transform(position,rotation);
                        camera.WorldTransform = root.WorldTransform;
                        if (order is "arms-first" or "current")
                        {
                            gun.SceneModel.Transform = gun.WorldTransform;
                            gun.SceneModel.Update(0);
                            arms.SceneModel.Transform = arms.WorldTransform;
                            arms.SceneModel.Update(0);
                        }
                        if (order is "clothing-first" or "current")
                            foreach(var layer in layers) { layer.SceneModel.Transform=layer.WorldTransform; layer.SceneModel.Update(0); }
                        apply.Invoke(clothing,new object[] { camera.WorldTransform });
                        // Complete the deferred render sync and re-pose from overrides, as the renderer does.
                        foreach (var renderer in root.Components.GetAll<SkinnedModelRenderer>(FindMode.EverythingInSelfAndDescendants))
                        {
                            if (!renderer.SceneModel.IsValid()) continue;
                            renderer.SceneModel.Transform=renderer.WorldTransform;
                            renderer.SceneModel.Update(0);
                            renderer.SceneModel.RenderingEnabled=renderer.Enabled && renderer.Active;
                        }
                        foreach (var renderer in bodyObject.GetComponentsInChildren<SkinnedModelRenderer>(true))
                            if(renderer.SceneModel.IsValid()) renderer.SceneModel.RenderingEnabled=false;
                        var eyes=(skin.SceneModel.GetBoneWorldTransform("eye_L").Position+skin.SceneModel.GetBoneWorldTransform("eye_R").Position)*.5f;
                        eyeError=Math.Max(eyeError,eyes.Distance(camera.WorldPosition));
                        foreach(var name in copiedNames)
                        {
                            if(!arms.Model.Bones.HasBone(name) || !skin.Model.Bones.HasBone(name)) continue;
                            var actual=skin.SceneModel.GetBoneWorldTransform(name);
                            // The engine can skip hidden skin fingers when gloves cover them. Compare the rendered
                            // pose to its stationary reference, including those bones, rather than to the bare arms.
                            var index=Enumerable.Range(0,skin.Model.BoneCount).First(i=>skin.Model.GetBoneName(i)==name);
                            var expected=camera.WorldTransform.ToWorld(reference[Array.IndexOf(layers,skin)][index]);
                            var error=actual.Position.Distance(expected.Position);
                            if(error>armError) worst=phase+" "+order+" "+position+" "+name;
                            armError=Math.Max(armError,error);
                            boneAngleError=Math.Max(boneAngleError,actual.Rotation.Distance(expected.Rotation));
                        }
                        for(int layerIndex=0;layerIndex<layers.Length;layerIndex++)
                        {
                            var layer=layers[layerIndex];
                            for(int bone=0;bone<layer.Model.BoneCount;bone++)
                            {
                                var expected=camera.WorldTransform.ToWorld(reference[layerIndex][bone]);
                                garmentError=Math.Max(garmentError,layer.SceneModel.GetBoneWorldTransform(bone).Position.Distance(expected.Position));
                            }
                        }
                        samples++;
                        if(prefabPath.Contains("kastov74u/") && phase=="hip" && order=="deferred" && position==new Vector3(0,0,10))
                        {
                            var imagePath=System.IO.Path.Combine(folder,$"ak74u-{style}-jump-after.png");
                            using var bitmap=new Bitmap(1280,720);
                            camera.RenderToBitmap(bitmap,false);
                            camera.RenderToBitmap(bitmap,false);
                            System.IO.File.WriteAllBytes(imagePath,bitmap.ToPng());
                            captures.Add(imagePath);
                        }
                    }
                }
            }
            var passed=eyeError<.01f && armError<.01f && garmentError<.01f && boneAngleError<.1f;
            var row=new { Prefab=prefabPath, Style=style.ToString(), Samples=samples, EyeError=eyeError, ArmDrift=armError, PoseDrift=garmentError, BoneAngleDrift=boneAngleError, Worst=worst, Passed=passed };
            rows.Add(row);
            if(!passed) failures.Add(row);
        }
    }
    catch(Exception e) { failures.Add(new { Prefab=prefabPath, Error=e.ToString() }); }
    finally { scene.Destroy(); }
}
System.IO.File.WriteAllText(System.IO.Path.Combine(folder,"validation.json"),Json.Serialize(new { Prefabs=prefabPaths.Length, Cases=rows, Failures=failures, Skipped=skipped }));
return new { Prefabs=prefabPaths.Length, OutfitCases=rows.Count, Failures=failures.Take(8).ToArray(), FailureCount=failures.Count, Skipped=skipped, Captures=captures };
