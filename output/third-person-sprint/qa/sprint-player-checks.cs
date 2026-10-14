var scene = new Scene();
var results = new System.Collections.Generic.List<object>();
var step = "start";
try
{
    using (scene.Push())
    {
        var root = new GameObject(true, "Isolated sprint player fixture");
        step = "create player";
        var player = root.Components.Create<Facepunch.PlayerPawn>(false);
        var health = root.Components.Create<Facepunch.HealthComponent>(false);
        player.HealthComponent = health;
        step = "create body";
        var bodyObject = new GameObject(root, true, "Body");
        var renderer = bodyObject.Components.Create<SkinnedModelRenderer>();
        renderer.Model = Model.Load(Facepunch.MilitaryUniform.HumanModelPath);
        renderer.CreateBoneObjects = true;
        var body = bodyObject.Components.Create<Facepunch.PlayerBody>(false);
        body.Renderer = renderer;
        body.Player = player;
        player.Body = body;
        var handObject = renderer.GetBoneObject("hand_R");
        step = "create hold";
        var hold = new GameObject(handObject, true, "WeaponHold");
        hold.LocalTransform = new Transform(new Vector3(5.808584f, -4.272694f, -2.632150f), new Rotation(.606300f, -.080075f, .071678f, -.787941f));
        player.HoldGameObject = hold;
        step = "clone gun";
        var weapon = Facepunch.LightweightCombatBot.WeaponPool().First(w => w.ResourceName == "m4a1");
        var gunObject = weapon.WorldModelPrefab.Clone(new CloneConfig { Parent = hold, StartEnabled = false });
        foreach (var component in gunObject.GetComponentsInChildren<Component>(true)) component.Enabled = component is ModelRenderer || component is Facepunch.WeaponModel;
        gunObject.Enabled = true;
        var gun = gunObject.GetComponentInChildren<Facepunch.WorldModel>();
        var equipmentObject = new GameObject(root, true, "Equipment");
        var equipment = equipmentObject.Components.Create<Facepunch.Equipment>(false);
        equipment.TagBinder = equipmentObject.Components.Create<Facepunch.TagBinder>(false);
        equipment.WorldModel = gun;
        step = "set current equipment";
        typeof(Facepunch.PlayerPawn).GetProperty("CurrentEquipment").SetValue(player, equipment);
        var apply = typeof(Facepunch.PlayerBody).GetMethod("ApplySprintPose", System.Reflection.BindingFlags.Instance | System.Reflection.BindingFlags.NonPublic);
        var blend = typeof(Facepunch.PlayerBody).GetField("_sprintPoseBlend", System.Reflection.BindingFlags.Instance | System.Reflection.BindingFlags.NonPublic);
        void Animate()
        {
            renderer.Set("holdtype", 2); renderer.Set("b_grounded", 1); renderer.Set("move_x", 310f); renderer.Set("move_groundspeed", 310f); renderer.Set("move_style", 2);
            scene.EditorTick(1f, .02f); renderer.SceneModel.Update(.02f);
        }
        Animate();
        step = "apply active sprint";
        player.IsSprinting = true;
        blend.SetValue(body, 1f);
        apply.Invoke(body, null);
        var mountError = gun.LocalPosition.Length;
        var right = renderer.Model.Bones.GetBone("hand_R");
        var boneObjectError = handObject.WorldPosition.Distance(renderer.SceneModel.GetBoneWorldTransform(right.Index).Position);
        results.Add(new { Case = "sprint active with migrated player socket", Passed = (float)blend.GetValue(body) > .99f && mountError < .001f && boneObjectError < .001f, MountError = mountError, BoneObjectError = boneObjectError });
        foreach (var stance in new[] { "crouch", "prone", "slide", "mantle", "pipe", "fall", "tablet", "pistol", "dead", "reload", "aim" })
        {
            step = "guard " + stance;
            Animate();
            blend.SetValue(body, 1f);
            switch (stance)
            {
                case "crouch": player.IsCrouching = true; break;
                case "prone": player.IsProne = true; break;
                case "slide": typeof(Facepunch.PlayerPawn).GetProperty("SlideBlend").SetValue(player, .5f); break;
                case "mantle": typeof(Facepunch.PlayerPawn).GetProperty("IsMantling").SetValue(player, true); break;
                case "pipe": typeof(Facepunch.PlayerPawn).GetProperty("IsPipeClimbing").SetValue(player, true); break;
                case "fall": typeof(Facepunch.PlayerPawn).GetProperty("IsFallKnockedDown", System.Reflection.BindingFlags.Instance | System.Reflection.BindingFlags.Public | System.Reflection.BindingFlags.NonPublic).SetValue(player, true); break;
                case "tablet": gun.UseTabletPose = true; break;
                case "pistol": typeof(Facepunch.Equipment).GetProperty("HoldType", System.Reflection.BindingFlags.Instance | System.Reflection.BindingFlags.NonPublic).SetValue(equipment, Facepunch.AnimationHelper.HoldTypes.Pistol); break;
                case "dead": typeof(Facepunch.HealthComponent).GetProperty("State").SetValue(health, Facepunch.LifeState.Dead); break;
                case "reload": var reload = equipmentObject.Components.Create<Facepunch.Reloadable>(false); typeof(Facepunch.EquipmentComponent).GetProperty("Equipment", System.Reflection.BindingFlags.Instance | System.Reflection.BindingFlags.NonPublic).SetValue(reload, equipment); reload.IsReloading = true; reload.Enabled = true; break;
                case "aim": equipment.SetTag("aiming"); break;
            }
            apply.Invoke(body, null);
            var value = (float)blend.GetValue(body);
            results.Add(new { Case = stance, Passed = stance == "aim" ? value < 1f : value == 0f, Blend = value });
            player.IsCrouching = false; player.IsProne = false;
            typeof(Facepunch.PlayerPawn).GetProperty("SlideBlend").SetValue(player, 0f);
            typeof(Facepunch.PlayerPawn).GetProperty("IsMantling").SetValue(player, false);
            typeof(Facepunch.PlayerPawn).GetProperty("IsPipeClimbing").SetValue(player, false);
            typeof(Facepunch.PlayerPawn).GetProperty("IsFallKnockedDown", System.Reflection.BindingFlags.Instance | System.Reflection.BindingFlags.Public | System.Reflection.BindingFlags.NonPublic).SetValue(player, false);
            gun.UseTabletPose = false;
            typeof(Facepunch.Equipment).GetProperty("HoldType", System.Reflection.BindingFlags.Instance | System.Reflection.BindingFlags.NonPublic).SetValue(equipment, Facepunch.AnimationHelper.HoldTypes.Rifle);
            typeof(Facepunch.HealthComponent).GetProperty("State").SetValue(health, Facepunch.LifeState.Alive);
            equipment.SetTag("aiming", false);
            foreach (var reload in equipmentObject.GetComponents<Facepunch.Reloadable>()) reload.Destroy();
        }
        return results;
    }
}
catch (Exception e) { return new { Step = step, Error = e.ToString(), Results = results }; }
finally { scene.Destroy(); }
