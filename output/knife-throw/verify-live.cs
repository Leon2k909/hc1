var player = Facepunch.Client.Local?.PlayerPawn;
if (!Game.IsPlaying || !Networking.IsHost || !player.IsValid())
    throw new InvalidOperationException("A local host player is required.");
var scene = Game.ActiveScene;
var inventory = player.Inventory;
var originalActive = player.CurrentEquipment?.Resource;
var originalKnife = inventory.Equipment.FirstOrDefault(e => e.Resource?.Slot == EquipmentSlot.Melee);
var originalResource = originalKnife?.Resource;
var originalAttachments = originalKnife?.ApplySavedAttachments ?? true;
var originalFrozen = player.IsFrozen;
var originalGodMode = player.HealthComponent.IsGodMode;
var initialDrops = scene.GetAllComponents<Facepunch.DroppedEquipment>().Select(d => d.Id).ToHashSet();
var initialFlights = scene.GetAllComponents<Facepunch.ThrownKnife>().Select(d => d.Id).ToHashSet();
var results = new System.Collections.Generic.List<object>();
GameObject target = null;
void Require(bool value, string message) { if (!value) throw new InvalidOperationException(message); }
async Task Wait(int ms) { await Task.Delay(ms, cancellationToken); Require(player.IsValid() && Game.ActiveScene == scene, "Player or scene changed during QA."); }
try
{
    player.HealthComponent.IsGodMode = true;
    var forward = player.EyeAngles.ToRotation().Forward;
    var start = player.EyePosition;
    var clear = scene.Trace.Ray(start, start + forward * 400f).Radius(16f)
        .IgnoreGameObjectHierarchy(player.GameObject).WithoutTags("trigger", "pickup", "movement").Run();
    Require(!clear.Hit, $"Aim is obstructed by {clear.GameObject?.Name}; no test objects were created.");
    target = new GameObject(scene, false, "Knife QA target");
    target.Flags |= GameObjectFlags.NotSaved;
    target.WorldPosition = start + forward * 350f;
    target.WorldRotation = Rotation.LookAt(forward, Vector3.Up);
    var collider = target.Components.Create<BoxCollider>();
    collider.Scale = new Vector3(24, 128, 192);
    var health = target.Components.Create<Facepunch.HealthComponent>();
    health.MaxHealth = 1000f;
    target.Enabled = true;
    await Wait(150);
    foreach (var resource in ResourceLibrary.GetAll<EquipmentResource>().Where(r => r.Slot == EquipmentSlot.Melee).OrderBy(r => r.ResourcePath).ToArray())
    {
        cancellationToken.ThrowIfCancellationRequested();
        foreach (var item in inventory.Equipment.Where(e => e.Resource?.Slot == EquipmentSlot.Melee).ToArray()) inventory.RemoveWeapon(item);
        var knife = inventory.Give(resource);
        Require(knife.IsValid(), $"Could not equip {resource.ResourceName}.");
        await Wait(300);
        var melee = knife.GetComponentInChildren<Facepunch.Melee>(true);
        Require(melee is not null && knife.IsDeployed, "Knife did not deploy.");
        player.IsFrozen = true;
        Require(!melee.TryThrowKnife(), "Frozen player could throw.");
        player.IsFrozen = false;
        Require(melee.TryThrowKnife(), "First throw request was rejected.");
        var other = inventory.Equipment.First(e => e != knife);
        inventory.Switch(other);
        await Wait(260);
        Require(knife.IsValid() && !melee.IsThrowingKnife && !scene.GetAllComponents<Facepunch.ThrownKnife>().Any(k => !initialFlights.Contains(k.Id)), "Holstering did not cancel the throw.");
        inventory.Switch(knife);
        await Wait(1100);
        var healthBefore = health.Health;
        int hits = 0;
        health.OnHealthChanged = (before, after) => { if (after < before) hits++; };
        Require(melee.TryThrowKnife(), "Throw after redeploy was rejected.");
        Require(!melee.TryThrowKnife(), "Duplicate throw was accepted.");
        await Wait(220);
        var flight = scene.GetAllComponents<Facepunch.ThrownKnife>().SingleOrDefault(k => !initialFlights.Contains(k.Id));
        Require(flight.IsValid(), "No projectile appeared after release.");
        Require(flight.Credit.Owner == player && flight.Credit.Resource == resource && !flight.Credit.Enabled, "Projectile lost weapon or attacker credit.");
        var flightPosition = flight.WorldPosition.ToString();
        var flightSpeed = flight.Velocity.Length;
        using (var frame = new Bitmap(1600, 900))
        {
            player.CameraController.Camera.RenderToBitmap(frame, false);
            System.IO.File.WriteAllBytes(System.IO.Path.Combine(Sandbox.Project.Current.GetRootPath(), $"output/knife-throw/{resource.ResourceName}-flight.png"), frame.ToPng());
        }
        await Wait(650);
        Require(!knife.IsValid(), "Thrown knife stayed in the inventory.");
        Require(!flight.IsValid(), "Projectile did not end on impact.");
        Require(hits == 1 && healthBefore - health.Health == 100f, $"Expected one 100-damage hit, got {hits} hits and {healthBefore - health.Health} damage.");
        var dropped = scene.GetAllComponents<Facepunch.DroppedEquipment>().SingleOrDefault(d => !initialDrops.Contains(d.Id) && d.Resource == resource);
        Require(dropped.IsValid(), "Impact did not create a pickup.");
        Require(player.CurrentEquipment.IsValid() && player.CurrentEquipment.Resource.Slot != EquipmentSlot.Melee, "Throw did not switch to another weapon.");
        dropped.OnUse(player);
        await Wait(180);
        var recovered = inventory.Equipment.SingleOrDefault(e => e.Resource == resource);
        Require(recovered.IsValid() && !dropped.IsValid(), "Pickup did not return exactly one knife.");
        inventory.Switch(recovered);
        await Wait(200);
        target.WorldPosition = player.AimRay.Position + player.AimRay.Forward * 40f;
        await Wait(80);
        var beforeSwing = health.Health;
        recovered.GetComponentInChildren<Facepunch.Melee>(true).Swing();
        await Wait(100);
        Require(recovered.IsValid() && health.Health < beforeSwing, "Primary melee attack did not remain available after recovery.");
        target.WorldPosition = player.EyePosition + player.EyeAngles.ToRotation().Forward * 350f;
        results.Add(new { Knife = resource.ResourceName, FrozenRejected = true, HolsterCancelled = true, DuplicateRejected = true, FlightPosition = flightPosition, FlightSpeed = flightSpeed, Damage = 100, ImpactCount = hits - 1, PickupRecovered = true, PrimaryStillSwings = true });
        health.OnHealthChanged = null;
    }
    return new { Scene = scene.Name, Results = results, LiveHost = true, RemoteClientTested = false };
}
finally
{
    if (target.IsValid()) target.Destroy();
    foreach (var flight in scene.GetAllComponents<Facepunch.ThrownKnife>().Where(k => !initialFlights.Contains(k.Id) && k.Credit?.Owner == player).ToArray()) flight.GameObject.Destroy();
    foreach (var drop in scene.GetAllComponents<Facepunch.DroppedEquipment>().Where(d => !initialDrops.Contains(d.Id) && d.Resource?.Slot == EquipmentSlot.Melee).ToArray()) drop.GameObject.Destroy();
    if (player.IsValid())
    {
        player.IsFrozen = originalFrozen;
        player.HealthComponent.IsGodMode = originalGodMode;
        foreach (var knife in inventory.Equipment.Where(e => e.Resource?.Slot == EquipmentSlot.Melee && e.Resource != originalResource).ToArray()) inventory.RemoveWeapon(knife);
        if (originalResource is not null && !inventory.Has(originalResource)) inventory.Give(originalResource, false, originalAttachments);
        var active = inventory.Equipment.FirstOrDefault(e => e.Resource == originalActive);
        if (active.IsValid()) inventory.Switch(active);
    }
}
