var vm = Game.ActiveScene.GetAllComponents<Facepunch.ViewModel>().FirstOrDefault(v => v.Enabled && v.Arms.IsValid());
if (vm is null) return "No viewmodel";
var gun = vm.ModelRenderer;
var arms = vm.Arms;
var skin = vm.GameObject.GetComponentsInChildren<SkinnedModelRenderer>().FirstOrDefault(r => r.GameObject.Name == "Clothing");
await Task.Delay(1000, cancellationToken);
var samples = new System.Collections.Generic.List<object>();
var timer = System.Diagnostics.Stopwatch.StartNew();
for (int i = 0; i < 180; i++)
{
    cancellationToken.ThrowIfCancellationRequested();
    if (!vm.IsValid() || !gun.SceneModel.IsValid() || !arms.SceneModel.IsValid()) break;
    var space = gun.SceneModel.Transform;
    Transform Local(SceneModel model, string bone) => space.ToLocal(model.GetBoneWorldTransform(bone));
    var left = Local(gun.SceneModel, "hand_L");
    var right = Local(gun.SceneModel, "hand_R");
    var target = Local(gun.SceneModel, "ik_hand_L");
    var source = Local(arms.SceneModel, "hand_L");
    var clothed = skin?.SceneModel.IsValid() == true ? Local(skin.SceneModel, "hand_L") : global::Transform.Zero;
    var sling = Local(gun.SceneModel, "tag_sling");
    samples.Add(new {
        Ms = timer.Elapsed.TotalMilliseconds, EngineTime = Time.Now,
        Left = left.Position, LeftRotation = left.Rotation, Right = right.Position,
        Target = target.Position, Source = source.Position, Clothing = clothed.Position,
        ClothingRotation = clothed.Rotation, Sling = sling.Position, SlingRotation = sling.Rotation,
        GunWorld = gun.WorldPosition, LeftError = left.Position.Distance(target.Position),
        MergeError = source.Position.Distance(left.Position), ClothingError = clothed.Position.Distance(source.Position),
        Yaw = gun.GetFloat("aim_yaw_inertia"), Pitch = gun.GetFloat("aim_pitch_inertia"),
        Bob = gun.GetFloat("move_bob"), HandIkWeight = gun.GetFloat("hand_ik_weight"), vm.AimProgress, Tags = vm.Equipment.GameObject.Tags.ToString()
    });
    await Task.Delay(16, cancellationToken);
}
var path = System.IO.Path.Combine(exchangeDirectory, "hand-jitter-after.json");
await System.IO.File.WriteAllTextAsync(path, Json.Serialize(samples), cancellationToken);
return new { Path = path, Resource = vm.Equipment.Resource.ResourcePath, Count = samples.Count, ElapsedMs = timer.Elapsed.TotalMilliseconds };
