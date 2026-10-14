var scene = Game.ActiveScene;
var player = Facepunch.Client.Local?.PlayerPawn;
return new {
    Game.IsPlaying, Scene = scene?.Name,
    RemainingTestObjects = scene.GetAllObjects(true).Where(g => g.Name is "Knife QA target" or "Knife input QA target").Select(g => g.Id).ToArray(),
    RemainingFlights = scene.GetAllComponents<Facepunch.ThrownKnife>().Select(k => k.Id).ToArray(),
    CurrentEquipment = player?.CurrentEquipment?.Resource?.ResourceName,
    Inventory = player?.Inventory?.Equipment.Select(e => new { e.Resource.ResourceName, e.Enabled }).ToArray(),
    ClassMenuOpen = Facepunch.UI.ClassSelect.IsAnyOpen,
    PlayerGodMode = player?.HealthComponent?.IsGodMode
};
