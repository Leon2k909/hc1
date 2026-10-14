var manifestPath = System.IO.Path.Combine(exchangeDirectory, "hand-graph-manifest.json");
if (!System.IO.File.Exists(manifestPath))
{
    var asset = Editor.AssetSystem.FindByPath("weapons/ak105/v_ak105.vmdl");
    var project = new System.IO.DirectoryInfo(System.IO.Path.GetDirectoryName(asset.AbsolutePath)).Parent.Parent.Parent.FullName;
    manifestPath = System.IO.Path.Combine(project, "output", "hand-jitter", "hand-graph-manifest.json");
}
var manifest = System.Text.Json.JsonSerializer.Deserialize<System.Collections.Generic.Dictionary<string,string>[]>(
    System.IO.File.ReadAllText(manifestPath));
var results = new System.Collections.Generic.List<object>();
foreach (var item in manifest)
{
    cancellationToken.ThrowIfCancellationRequested();
    var scene = new Scene();
    try
    {
        using var scope = scene.Push();
        var model = Model.Load(item["Resource"].Replace(".vanmgrph", ".vmdl"));
        var original = new SceneModel(scene.SceneWorld, model, global::Transform.Zero);
        var settled = new SceneModel(scene.SceneWorld, model, global::Transform.Zero);
        original.SetAnimParameter("hand_ik_weight", 1f);
        settled.SetAnimParameter("hand_ik_weight", 0f);
        for (int i=0;i<180;i++) { original.Update(1f/60f); settled.Update(1f/60f); }
        float maxGunDifference = 0, maxHandDifference = 0, idleJitter = 0;
        var previous = settled.GetBoneWorldTransform("hand_L").Position;
        for(int i=0;i<180;i++)
        {
            float dt = i%3==0 ? 1f/30f : i%3==1 ? 1f/60f : 1f/144f;
            settled.Update(dt);
            var hand = settled.GetBoneWorldTransform("hand_L").Position;
            idleJitter = Math.Max(idleJitter, hand.Distance(previous));
            previous = hand;
        }
        // Bring both instances back to the same clock after the idle jitter sample.
        original.Delete(); settled.Delete();
        original = new SceneModel(scene.SceneWorld, model, global::Transform.Zero);
        settled = new SceneModel(scene.SceneWorld, model, global::Transform.Zero);
        original.SetAnimParameter("hand_ik_weight", 1f);
        settled.SetAnimParameter("hand_ik_weight", 0f);
        for (int i=0;i<180;i++) { original.Update(1f/60f); settled.Update(1f/60f); }
        foreach (var phase in new[] { "ADS", "aimed reload", "sprint", "fire", "walk", "sway", "lowered", "deploy" })
        {
            float sinceMotion = 3f;
            for (int i=0;i<480;i++)
            {
                cancellationToken.ThrowIfCancellationRequested();
                var aim = phase == "ADS" ? Math.Min(i/30f,1f) : phase == "aimed reload" ? 1f : 0f;
                var reload = phase == "aimed reload" && i<240;
                var sprint = phase == "sprint" && i<120;
                var walk = phase == "walk" && i<120;
                var sway = phase == "sway" && i<12;
                var lower = phase == "lowered" && i<120;
                var fire = phase == "fire" && i==0;
                var deploy = phase == "deploy" && i==0;
                if ((phase == "ADS" && i<=30) || reload || sprint || walk || sway || lower
                    || (phase == "fire" && i<15) || deploy || i==0) sinceMotion = 0;
                settled.SetAnimParameter("hand_ik_weight", sinceMotion < 2f ? 1f : 0f);
                foreach(var sm in new[] { original, settled })
                {
                    sm.SetAnimParameter("ironsights_weight", aim);
                    sm.SetAnimParameter("b_reload", reload ? 1 : 0);
                    sm.SetAnimParameter("b_sprint", sprint ? 1 : 0);
                    sm.SetAnimParameter("b_lower_weapon", lower ? 1 : 0);
                    sm.SetAnimParameter("b_attack", fire ? 1 : 0);
                    sm.SetAnimParameter("b_deploy", deploy ? 1 : 0);
                    sm.SetAnimParameter("move_bob", walk ? 1f : 0f);
                    sm.SetAnimParameter("aim_yaw_inertia", sway ? -40f : 0f);
                    sm.Update(1f/60f);
                }
                sinceMotion += 1f/60f;
                maxGunDifference = Math.Max(maxGunDifference, original.GetBoneWorldTransform("tag_sling").Position.Distance(settled.GetBoneWorldTransform("tag_sling").Position));
                maxHandDifference = Math.Max(maxHandDifference, original.GetBoneWorldTransform("hand_L").Position.Distance(settled.GetBoneWorldTransform("hand_L").Position));
            }
        }
        results.Add(new { Graph = item["Resource"], IdleJitter = idleJitter, GunDifference = maxGunDifference,
            HandDifference = maxHandDifference, Passed = idleJitter < 0.0001f && maxGunDifference < 0.001f && maxHandDifference < 0.025f });
        original.Delete(); settled.Delete();
    }
    finally { scene.Destroy(); }
}
System.IO.File.WriteAllText(System.IO.Path.Combine(exchangeDirectory,"settled-hand-policy-regressions.json"), Json.Serialize(results));
var json = System.Text.Json.JsonSerializer.Serialize(results);
var rows = System.Text.Json.JsonDocument.Parse(json).RootElement.EnumerateArray().ToArray();
return new { Count = rows.Length, Passed = rows.Count(r => r.GetProperty("Passed").GetBoolean()),
    MaxIdleJitter = rows.Max(r=>r.GetProperty("IdleJitter").GetSingle()), MaxGunDifference = rows.Max(r=>r.GetProperty("GunDifference").GetSingle()),
    MaxHandDifference = rows.Max(r=>r.GetProperty("HandDifference").GetSingle()), Failures = rows.Where(r=>!r.GetProperty("Passed").GetBoolean()).ToArray() };
