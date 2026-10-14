var scene = Game.ActiveScene;
var results = new System.Collections.Generic.List<object>();
var sprintErrors = new System.Collections.Generic.List<float>();
var mountErrors = new System.Collections.Generic.List<float>();
var peakBlend = 0f;
var returning = 0;
var reloadOverrides = 0;
var slideOverrides = 0;
var blendField = typeof(Facepunch.LightweightCombatBot).GetField("_sprintPoseBlend", System.Reflection.BindingFlags.NonPublic | System.Reflection.BindingFlags.Instance);
var supportField = typeof(Facepunch.LightweightCombatBot).GetField("_supportGripWeight", System.Reflection.BindingFlags.NonPublic | System.Reflection.BindingFlags.Instance);
for (var frame = 0; frame < 120 && scene.IsValid() && Game.ActiveScene == scene; frame++)
{
    await Task.Delay(25, cancellationToken);
    foreach (var bot in scene.GetAllComponents<Facepunch.LightweightCombatBot>())
    {
        if (!bot.IsAlive || !bot.Renderer.IsValid() || !bot.Renderer.SceneModel.IsValid()) continue;
        var blend = (float)blendField.GetValue(bot);
        peakBlend = MathF.Max(peakBlend, blend);
        if (blend > 0f && blend < 1f) returning++;
        if (bot.IsReloading && blend > 0f) reloadOverrides++;
        if (bot.SlideBlend > 0f && blend > 0f) slideOverrides++;
        if (blend <= 0f || (float)supportField.GetValue(bot) < .999f) continue;
        var body = bot.Renderer;
        var gun = bot.GetComponentInChildren<Facepunch.WorldModel>();
        if (!gun.IsValid() || !gun.IkLeftHand.IsValid()) continue;
        var left = body.Model.Bones.GetBone("hand_L");
        var right = body.Model.Bones.GetBone("hand_R");
        sprintErrors.Add(body.SceneModel.GetBoneWorldTransform(left.Index).Position.Distance(gun.IkLeftHand.WorldPosition));
        mountErrors.Add(body.SceneModel.GetBoneWorldTransform(right.Index).WithScale(1f).ToWorld(Facepunch.MilitaryUniform.WeaponHandOffset(body.Model)).Position.Distance(gun.WorldPosition));
    }
}
var player = scene.IsValid() ? scene.GetAllComponents<Facepunch.PlayerPawn>().FirstOrDefault() : null;
var playerMount = player?.CurrentEquipment?.WorldModel;
var playerRight = player?.BodyRenderer?.Model?.Bones.GetBone("hand_R");
return new { Scene = scene.Name, Samples = sprintErrors.Count, PeakBlend = peakBlend, TransitionSamples = returning, ReloadOverrides = reloadOverrides, SlideOverrides = slideOverrides, LeftErrorAverage = sprintErrors.Count > 0 ? sprintErrors.Average() : -1f, LeftErrorMax = sprintErrors.Count > 0 ? sprintErrors.Max() : -1f, RightMountMax = mountErrors.Count > 0 ? mountErrors.Max() : -1f, PlayerGunInHand = playerMount.IsValid() && playerRight is not null ? (object)player.BodyRenderer.SceneModel.GetBoneWorldTransform(playerRight.Index).WithScale(1f).ToLocal(playerMount.WorldTransform) : null, ExpectedPlayerMount = playerRight is not null ? (object)Facepunch.MilitaryUniform.WeaponHandOffset(player.BodyRenderer.Model) : null };
