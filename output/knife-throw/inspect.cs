var player = Facepunch.Client.Local?.PlayerPawn;
return new {
    Game.IsPlaying, Networking.IsHost, Scene = Game.ActiveScene?.Name,
    Player = player?.GameObject.Id, Frozen = player?.IsFrozen,
    Position = player?.WorldPosition.ToString(), Eyes = player?.EyePosition.ToString(),
    Health = player?.HealthComponent?.Health, State = player?.HealthComponent?.State.ToString(),
    Local = player?.IsLocallyControlled, Viewer = player?.IsViewer, Suppressed = Input.Suppressed,
    ClassMenu = Facepunch.UI.ClassSelect.IsAnyOpen, BuyMenu = Facepunch.UI.TacticalBuyMenu.IsAnyOpen,
    KnifeEnabled = player?.Inventory?.Equipment.FirstOrDefault(e => e.Resource?.Slot == EquipmentSlot.Melee)?.GetComponentInChildren<Facepunch.Melee>(true)?.Enabled,
    Active = player?.CurrentEquipment?.Resource?.ResourceName,
    Inventory = player?.Inventory?.Equipment.Select(e => new { e.Resource.ResourceName, e.IsDeployed }).ToArray(),
    Knives = ResourceLibrary.GetAll<EquipmentResource>().Where(r => r.Slot == EquipmentSlot.Melee).Select(r => new {
        r.ResourcePath, Model = r.WorldModel?.ResourcePath, Bounds = r.WorldModel?.Bounds.ToString(),
        Throwing = r.MainPrefab?.GetComponentInChildren<Facepunch.Melee>(true)?.ThrowSpeed }).ToArray(),
    Flights = Game.ActiveScene?.GetAllComponents<Facepunch.ThrownKnife>().Select(k => new { k.GameObject.Id, Position = k.WorldPosition.ToString(), Velocity = k.Velocity.ToString() }).ToArray()
};
