using var state = System.Text.Json.JsonDocument.Parse(System.IO.File.ReadAllText(System.IO.Path.Combine(Sandbox.Project.Current.GetRootPath(), "output/knife-throw/input-state.json")));
var data = state.RootElement;
var scene = Game.ActiveScene;
if (scene.Id != data.GetProperty("SceneId").GetGuid()) throw new InvalidOperationException("The test scene has changed.");
var player = scene.Directory.FindComponentByGuid(data.GetProperty("PlayerId").GetGuid()) as Facepunch.PlayerPawn;
var target = scene.GetAllObjects(true).FirstOrDefault(g => g.Id == data.GetProperty("TargetId").GetGuid());
var resource = ResourceLibrary.Get<EquipmentResource>(data.GetProperty("KnifeResource").GetString());
var originalDrops = data.GetProperty("OriginalDrops").EnumerateArray().Select(v => v.GetGuid()).ToHashSet();
var originalFlights = data.GetProperty("OriginalFlights").EnumerateArray().Select(v => v.GetGuid()).ToHashSet();
try
{
    await Task.Delay(500, cancellationToken);
    var damage = 1000f - target.GetComponent<Facepunch.HealthComponent>().Health;
    bool consumed = !player.Inventory.Has(resource);
    bool emptyHands = !player.CurrentEquipment.IsValid();
    var drop = scene.GetAllComponents<Facepunch.DroppedEquipment>().FirstOrDefault(d => d.Resource == resource && !originalDrops.Contains(d.Id));
    bool pickupExists = drop.IsValid();
    if (drop.IsValid()) drop.OnUse(player);
    await Task.Delay(100, cancellationToken);
    bool recovered = player.Inventory.Has(resource);
    var result = new { SecondaryInputTriggered = consumed, KnifeOnlyInventory = data.GetProperty("InventoryCount").GetInt32() == 1, EmptyHandsAfterRelease = emptyHands, Damage = damage, PickupExists = pickupExists, Recovered = recovered };
    System.IO.File.WriteAllText(System.IO.Path.Combine(Sandbox.Project.Current.GetRootPath(), "output/knife-throw/input-verification.json"), Json.Serialize(result));
    if (!consumed || !emptyHands || damage != 100f || !pickupExists || !recovered) throw new InvalidOperationException(Json.Serialize(result));
    return result;
}
finally
{
    if (target.IsValid()) target.Destroy();
    foreach (var flight in scene.GetAllComponents<Facepunch.ThrownKnife>().Where(k => !originalFlights.Contains(k.Id)).ToArray()) flight.GameObject.Destroy();
    foreach (var drop in scene.GetAllComponents<Facepunch.DroppedEquipment>().Where(d => d.Resource == resource && !originalDrops.Contains(d.Id)).ToArray()) drop.GameObject.Destroy();
    if (player.IsValid())
    {
        player.HealthComponent.IsGodMode = data.GetProperty("OriginalGodMode").GetBoolean();
        foreach (var id in data.GetProperty("Others").EnumerateArray())
        {
            var other = scene.Directory.FindComponentByGuid(id.GetGuid());
            if (other.IsValid()) other.Enabled = true;
        }
        if (!player.Inventory.Has(resource)) player.Inventory.Give(resource, false);
        var active = scene.Directory.FindComponentByGuid(data.GetProperty("ActiveId").GetGuid()) as Facepunch.Equipment;
        if (active.IsValid()) player.Inventory.Switch(active);
        if (data.GetProperty("ClassMenuOpen").GetBoolean()) Facepunch.UI.ClassSelect.OpenAny();
    }
}
