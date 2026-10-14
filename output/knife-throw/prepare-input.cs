var player = Facepunch.Client.Local?.PlayerPawn;
if (!Game.IsPlaying || !Networking.IsHost || !player.IsValid()) throw new InvalidOperationException("Local host player required.");
var scene = Game.ActiveScene;
var inventory = player.Inventory;
var knife = inventory.Equipment.First(e => e.Resource?.Slot == EquipmentSlot.Melee);
var originalActive = player.CurrentEquipment;
var others = inventory.Equipment.Where(e => e != knife).ToArray();
var originalGodMode = player.HealthComponent.IsGodMode;
var classMenuOpen = Facepunch.UI.ClassSelect.IsAnyOpen;
GameObject target = null;
bool ready = false;
try
{
    var start = player.EyePosition;
    var forward = player.EyeAngles.ToRotation().Forward;
    var trace = scene.Trace.Ray(start, start + forward * 400f).Radius(16f).IgnoreGameObjectHierarchy(player.GameObject).WithoutTags("trigger", "pickup", "movement").Run();
    if (trace.Hit) throw new InvalidOperationException("Aim is obstructed; input test not started.");
    player.HealthComponent.IsGodMode = true;
    var panel = typeof(Facepunch.UI.ClassSelect).GetProperty("Instance", System.Reflection.BindingFlags.NonPublic | System.Reflection.BindingFlags.Static).GetValue(null);
    if (panel is not null) typeof(Facepunch.UI.ClassSelect).GetProperty("IsOpen", System.Reflection.BindingFlags.NonPublic | System.Reflection.BindingFlags.Instance).SetValue(panel, false);
    inventory.Switch(knife);
    await Task.Delay(1200, cancellationToken);
    foreach (var other in others) other.Enabled = false;
    target = new GameObject(scene, false, "Knife input QA target");
    target.Flags |= GameObjectFlags.NotSaved;
    target.WorldPosition = start + forward * 350f;
    target.WorldRotation = Rotation.LookAt(forward, Vector3.Up);
    target.Components.Create<BoxCollider>().Scale = new Vector3(24, 128, 192);
    var health = target.Components.Create<Facepunch.HealthComponent>();
    health.MaxHealth = 1000f;
    target.Enabled = true;
    var state = new {
        PlayerId = player.Id, TargetId = target.Id, KnifeId = knife.Id, KnifeResource = knife.Resource.ResourcePath,
        ActiveId = originalActive?.Id, OriginalGodMode = originalGodMode, ClassMenuOpen = classMenuOpen, Others = others.Select(e => e.Id).ToArray(),
        OriginalDrops = scene.GetAllComponents<Facepunch.DroppedEquipment>().Select(d => d.Id).ToArray(),
        OriginalFlights = scene.GetAllComponents<Facepunch.ThrownKnife>().Select(d => d.Id).ToArray(),
        InventoryCount = inventory.Equipment.Count(), SceneId = scene.Id,
        MenuClosed = !Facepunch.UI.ClassSelect.IsAnyOpen, IsLocal = player.IsLocallyControlled,
        CanSwing = knife.GetComponentInChildren<Facepunch.Melee>(true).CanSwing(), knife.IsDeployed
    };
    System.IO.File.WriteAllText(System.IO.Path.Combine(Sandbox.Project.Current.GetRootPath(), "output/knife-throw/input-state.json"), Json.Serialize(state));
    ready = true;
    return state;
}
finally
{
    if (!ready)
    {
        if (target.IsValid()) target.Destroy();
        if (player.IsValid()) player.HealthComponent.IsGodMode = originalGodMode;
        foreach (var other in others) if (other.IsValid()) other.Enabled = true;
        if (originalActive.IsValid()) inventory.Switch(originalActive);
        if (classMenuOpen) Facepunch.UI.ClassSelect.OpenAny();
    }
}
