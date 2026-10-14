var weapons = Facepunch.LightweightCombatBot.WeaponPool().OrderBy(w => w.ResourceName).ToArray();
var report = new System.Collections.Generic.List<object>();
var errors = new System.Collections.Generic.List<string>();
var totalPoses = 0;
var maxLeftError = 0f;
var maxRightError = 0f;
var maxLengthError = 0f;
var details = new System.Collections.Generic.List<object>();
foreach (var weapon in weapons)
{
    cancellationToken.ThrowIfCancellationRequested();
    var scene = new Scene();
    try
    {
        using (scene.Push())
        {
            var body = new GameObject(true, "Sprint pool fixture").Components.Create<SkinnedModelRenderer>();
            body.Model = Model.Load(Facepunch.MilitaryUniform.HumanModelPath);
            body.AnimationGraph = AnimationGraph.Load("animgraphs/human_bot.vanmgrph");
            body.WorldRotation = Rotation.FromYaw(67f);
            var gunObject = weapon.WorldModelPrefab.Clone(new CloneConfig { StartEnabled = false, Transform = new() });
            foreach (var component in gunObject.GetComponentsInChildren<Component>(true)) component.Enabled = component is ModelRenderer || component is Facepunch.WeaponModel;
            gunObject.Enabled = true;
            var gun = gunObject.GetComponentInChildren<Facepunch.WorldModel>();
            if (!gun.IsValid() || !gun.IkLeftHand.IsValid()) { errors.Add(weapon.ResourceName + ": no support grip"); continue; }
            var sprint = new Facepunch.ThirdPersonSprintPose();
            var right = body.Model.Bones.GetBone("hand_R");
            var left = body.Model.Bones.GetBone("hand_L");
            var offset = Facepunch.MilitaryUniform.WeaponHandOffset(body.Model);
            var time = 0f;
            var gunLeftMax = 0f;
            for (var frame = 0; frame < 32; frame++)
            {
                var blend = frame < 16 ? MathF.Min(1f, frame / 8f) : MathF.Max(0f, (31-frame) / 8f);
                body.Set("holdtype", 2); body.Set("b_grounded", 1); body.Set("b_twohanded", 1);
                body.Set("move_groundspeed", 310f); body.Set("move_speed", 310f); body.Set("move_x", 310f); body.Set("wish_x", 310f); body.Set("move_style", 2);
                body.Set("_human_sprint_rate_per_inch", 1.25f/310f);
                body.SetLookDirection("aim_body", body.WorldRotation.Forward, .75f);
                scene.EditorTick(time += .05f, .05f); body.SceneModel.Transform = body.WorldTransform; body.SceneModel.Update(.05f);
                gun.WorldTransform = body.SceneModel.GetBoneWorldTransform(right.Index).WithScale(1f).ToWorld(offset);
                var bones = new[] { "arm_upper_R", "arm_lower_R", "hand_R", "arm_upper_L", "arm_lower_L", "hand_L" }.Select(name => body.Model.Bones.GetBone(name)).ToArray();
                var poses = bones.Select(b => body.SceneModel.GetBoneWorldTransform(b.Index)).ToArray();
                var beforeLengths = new[] { poses[0].Position.Distance(poses[1].Position), poses[1].Position.Distance(poses[2].Position), poses[3].Position.Distance(poses[4].Position), poses[4].Position.Distance(poses[5].Position) };
                var beforeGun = gun.WorldTransform;
                var applied = sprint.Apply(body, gun, blend, updateBoneObjects: false);
                if (blend <= 0f) { if (applied || gun.WorldPosition.Distance(beforeGun.Position) > .001f) errors.Add(weapon.ResourceName + ": inactive carry moved the gun"); continue; }
                if (!applied) { errors.Add(weapon.ResourceName + ": active carry rejected"); continue; }
                totalPoses++;
                var after = bones.Select(b => body.SceneModel.GetBoneWorldTransform(b.Index)).ToArray();
                var rightError = after[2].WithScale(1f).ToWorld(offset).Position.Distance(gun.WorldPosition);
                var leftError = after[5].Position.Distance(gun.IkLeftHand.WorldTransform.Position);
                var afterLengths = new[] { after[0].Position.Distance(after[1].Position), after[1].Position.Distance(after[2].Position), after[3].Position.Distance(after[4].Position), after[4].Position.Distance(after[5].Position) };
                var lengthError = beforeLengths.Zip(afterLengths, (a,b) => MathF.Abs(a-b)).Max();
                gunLeftMax = MathF.Max(gunLeftMax, leftError);
                maxLeftError = MathF.Max(maxLeftError, leftError); maxRightError = MathF.Max(maxRightError, rightError); maxLengthError = MathF.Max(maxLengthError, lengthError);
                if (leftError > .15f || rightError > .001f || lengthError > .001f) errors.Add($"{weapon.ResourceName} blend={blend}: left={leftError} mount={rightError} length={lengthError}");
                if (weapon.ResourceName == "ak12" && frame < 5) details.Add(new { Frame = frame, Blend = blend, Gun = body.WorldTransform.ToLocal(gun.WorldTransform), LeftShoulder = body.WorldTransform.PointToLocal(after[3].Position), RightShoulder = body.WorldTransform.PointToLocal(after[0].Position), RightWrist = body.WorldTransform.PointToLocal(after[2].Position), LeftWrist = body.WorldTransform.PointToLocal(after[5].Position), LeftTarget = body.WorldTransform.PointToLocal(gun.IkLeftHand.WorldPosition), LeftLength = afterLengths[2] + afterLengths[3], RightLength = afterLengths[0] + afterLengths[1] });
            }
            report.Add(new { Weapon = weapon.ResourceName, MaxLeftError = gunLeftMax });
        }
    }
    finally { scene.Destroy(); }
    await Task.Delay(10, cancellationToken);
}
var summary = new { Weapons = report.Count, Poses = totalPoses, MaxLeftError = maxLeftError, MaxRightMountError = maxRightError, MaxArmLengthChange = maxLengthError, Failures = errors, Report = report };
var path = @"D:\Documents\s&box projects\hc1\forked-shooter-main\output\third-person-sprint\pool-checks.json";
System.IO.File.WriteAllText(path, System.Text.Json.JsonSerializer.Serialize(summary, new System.Text.Json.JsonSerializerOptions { WriteIndented = true }));
return new { Weapons = report.Count, Poses = totalPoses, MaxLeftError = maxLeftError, MaxRightMountError = maxRightError, MaxArmLengthChange = maxLengthError, Failures = errors, ReportPath = path, Details = details };
