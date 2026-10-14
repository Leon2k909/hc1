var applySprint = true;
var folder = @"D:\Documents\s&box projects\hc1\forked-shooter-main\output\third-person-sprint";
System.IO.Directory.CreateDirectory(folder);
var weapons = Facepunch.LightweightCombatBot.WeaponPool().Where(w => new[] { "m4a1", "kastov74u", "rpk", "aug" }.Contains(w.ResourceName.Replace("weapon_", "").ToLowerInvariant())).OrderBy(w => w.ResourceName).ToArray();
var report = new System.Collections.Generic.List<object>();
using var sheet = new Bitmap(1440, weapons.Length * 480);
sheet.Clear(Color.Black);
for (var wi = 0; wi < weapons.Length; wi++)
{
    cancellationToken.ThrowIfCancellationRequested();
    var weapon = weapons[wi];
    var scene = new Scene();
    try
    {
        using (scene.Push())
        {
            var body = new GameObject(true, "Sprint preview").Components.Create<SkinnedModelRenderer>();
            body.Model = Model.Load(Facepunch.MilitaryUniform.HumanModelPath);
            Facepunch.MilitaryUniform.SetModel(body, body.Model, wi % 2 == 0 ? Facepunch.MilitaryUniformStyle.Standard : Facepunch.MilitaryUniformStyle.Field);
            body.AnimationGraph = AnimationGraph.Load("animgraphs/human_bot.vanmgrph");
            var gunObject = weapon.WorldModelPrefab.Clone(new CloneConfig { StartEnabled = false, Transform = new() });
            foreach (var component in gunObject.GetComponentsInChildren<Component>(true)) component.Enabled = component is ModelRenderer || component is Facepunch.WeaponModel;
            gunObject.Enabled = true;
            var gun = gunObject.GetComponentInChildren<Facepunch.WorldModel>();
            gun.ModelRenderer.SetBodyGroup("sight", 0);
            gun.ModelRenderer.SetBodyGroup("muzzle", 0);
            var camera = new GameObject(true, "Sprint preview camera").Components.Create<CameraComponent>();
            camera.BackgroundColor = new Color(.10f, .12f, .15f);
            camera.FieldOfView = 42f;
            camera.ZNear = 1f;
            var light = new GameObject(true, "Sprint preview light").Components.Create<DirectionalLight>();
            light.WorldRotation = Rotation.From(40f, 150f, 0f);
            light.LightColor = Color.White * 2f;
            light.SkyColor = Color.White * .6f;
            var grip = new Facepunch.BotSupportHand(true);
            var support = new Facepunch.BotSupportHand();
            var fit = new Facepunch.BotWeaponPose();
            var sprint = new Facepunch.ThirdPersonSprintPose();
            var right = body.Model.Bones.GetBone("hand_R");
            var offset = Facepunch.MilitaryUniform.WeaponHandOffset(body.Model);
            scene.EditorTick(.016f, .016f);
            for (var i = 0; i < 24; i++)
            {
                body.Set("holdtype", 2);
                body.Set("holdtype_handedness", 1);
                body.Set("b_grounded", 1);
                body.Set("b_twohanded", 1);
                body.Set("move_speed", 310f);
                body.Set("move_groundspeed", 310f);
                body.Set("move_x", 310f);
                body.Set("wish_x", 310f);
                body.Set("move_style", 2);
                body.Set("_human_sprint_rate_per_inch", 1.1f / 310f);
                body.SetLookDirection("aim_body", Vector3.Forward, .75f);
                body.SetLookDirection("aim_head", Vector3.Forward, 1f);
                body.SetLookDirection("aim_eyes", Vector3.Forward, 1f);
                body.Set("ik.hand_right.enabled", 0);
                scene.EditorTick((i + 1) * .05f, .05f);
                foreach (var renderer in body.GetComponentsInChildren<SkinnedModelRenderer>(true)) renderer.SceneModel?.Update(.05f);
                gun.WorldTransform = body.SceneModel.GetBoneWorldTransform(right.Index).WithScale(1f).ToWorld(offset);
                if (applySprint) { sprint.Apply(body, gun, 1f, updateBoneObjects: false); continue; }
                var wrist = body.SceneModel.GetBoneWorldTransform(right.Index);
                var shift = fit.Fit(body, gun, support, grip, wrist.Position, 1f);
                grip.Apply(body, wrist.WithPosition(wrist.Position + shift));
                gun.WorldTransform = body.SceneModel.GetBoneWorldTransform(right.Index).WithScale(1f).ToWorld(offset);
                var left = Facepunch.MilitaryUniform.HandIkTransform(body.Model, "hand_left", body.WorldTransform.ToLocal(gun.IkLeftHand.WorldTransform));
                support.Apply(body, body.WorldTransform.ToWorld(left));
            }
            var cameraPositions = new[] { new Vector3(15f, 106f, 61f), new Vector3(105f, -55f, 58f), new Vector3(15f, -106f, 61f) };
            using var tile = new Bitmap(480, 480);
            for (var view = 0; view < cameraPositions.Length; view++)
            {
                camera.WorldPosition = cameraPositions[view];
                camera.WorldRotation = Rotation.LookAt(new Vector3(5f, 0f, 38f) - camera.WorldPosition);
                foreach (var renderer in gunObject.GetComponentsInChildren<SkinnedModelRenderer>(true)) { if (renderer.SceneModel is null) continue; renderer.SceneModel.Transform = renderer.WorldTransform; renderer.SceneModel.Update(0f); }
                camera.RenderToBitmap(tile);
                sheet.DrawBitmap(tile, new Rect(view * 480, wi * 480, 480, 480));
            }
            report.Add(new { Weapon = weapon.ResourceName, Gun = body.WorldTransform.ToLocal(gun.WorldTransform), Shoulder = body.SceneModel.GetBoneWorldTransform(body.Model.Bones.GetBone("arm_upper_R").Index).Position });
        }
    }
    finally { scene.Destroy(); }
    await Task.Delay(20, cancellationToken);
}
var path = System.IO.Path.Combine(folder, applySprint ? "after.png" : "before.png");
System.IO.File.WriteAllBytes(path, sheet.ToPng());
return new { Path = path, Weapons = report };
