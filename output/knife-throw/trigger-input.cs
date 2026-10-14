var player = Facepunch.Client.Local?.PlayerPawn;
var melee = player?.CurrentEquipment?.GetComponentInChildren<Facepunch.Melee>(true);
if (melee is null) throw new InvalidOperationException("Equip the QA knife first.");
var action = typeof(Facepunch.WeaponInputAction).GetMethod("OnFixedUpdate", System.Reflection.BindingFlags.NonPublic | System.Reflection.BindingFlags.Instance);
try
{
    Input.SetAction("Attack2", false);
    action.Invoke(melee, null);
    Input.SetAction("Attack2", true);
    var inputIsDown = Input.Down("Attack2");
    action.Invoke(melee, null);
    return new { InputIsDown = inputIsDown, melee.IsThrowingKnife, melee.IsTakingInput, player.IsLocallyControlled, MenuOpen = Facepunch.UI.ClassSelect.IsAnyOpen };
}
finally { Input.SetAction("Attack2", false); }
