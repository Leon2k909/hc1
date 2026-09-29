namespace Facepunch.Gunsmith;

/// <summary>
/// The manager for gunsmith, we'll place this in the gunsmith scene and handle state.
/// </summary>
public partial class GunsmithSystem : Component
{
	private const string ScarHResourcePath = "weapons/scarh/scarh.equip";
	private const string ScarHGunsmithModelPath = "weapons/swb/scarh/v_scarh_gunsmith.vmdl";
	private const string Mp5ResourcePath = "weapons/mp5/mp5.equip";
	private string appliedMp5Stock;
	private bool loadingEquipment;

	[Property]
	public EquipmentResource Equipment { get; set; }

	[Property]
	public SkinnedModelRenderer Renderer { get; set; }

	[Property]
	public GunsmithController Controller { get; set; }

	public GunsmithWeapon Weapon => Controller.IsValid() ? Controller.Weapon : null;

	/// <summary>
	/// Are we in FPS mode?
	/// </summary>
	public bool FPS { get; private set; } = false;

	/// <summary>
	/// Sets the FPS mode
	/// </summary>
	/// <param name="fps"></param>
	public void SetFirstPerson( bool fps )
	{
		var weapon = Weapon;

		if ( !Renderer.IsValid() || !weapon.IsValid() || !weapon.ViewModel.IsValid() || !Controller.IsValid() || !Controller.CameraComponent.IsValid() )
			return;

		FPS = fps;
		Renderer.UseAnimGraph = fps;
		if ( weapon.ViewModel.Arms.IsValid() && weapon.ViewModel.Arms != Renderer )
		{
			weapon.ViewModel.Arms.Enabled = false;
		}

		if ( fps )
		{
			Renderer.GameObject.SetParent( Controller.CameraComponent.GameObject, false );
			Renderer.LocalPosition = 0;
		}
		else
		{
			// Most guns' renderer is the prefab's root. The 1911's is a child, which goes back under the root: moved out
			// here it didn't turn or frame with the gun, and loading the next gun left it on the stage.
			var parent = Renderer.GameObject == weapon.GameObject ? GameObject : weapon.GameObject;
			Renderer.GameObject.SetParent( parent, false );
			Renderer.LocalPosition = Equipment.GunsmithOffset;
		}

		HidePreviewArms( weapon.GameObject, Renderer );
	}

	[Button( "Toggle FPS" )]
	public void Toggle()
	{
		if ( !Renderer.IsValid() || !Weapon.IsValid() || !Scene.IsValid() )
			return;

		SetFirstPerson( !FPS );

		// Reset all jiggle bones
		foreach ( var bone in Scene.GetAllComponents<JiggleBone>() )
		{
			if ( !bone.IsValid() )
				continue;

			bone.ResetState();
		}
	}

	protected override void OnStart()
	{
		ConfigureStudioView();
		LoadEquipment( GetInitialEquipment() );
	}

	protected override void OnDestroy()
	{
		if ( Controller.IsValid() && Controller.CameraComponent.IsValid() )
			Controller.CameraComponent.Enabled = false;
	}

	private void ConfigureStudioView()
	{
		if ( !Controller.IsValid() || !Controller.CameraComponent.IsValid() )
			return;

		var camera = Controller.CameraComponent;
		camera.Enabled = true;
		camera.IsMainCamera = true;
		camera.Priority = 100;

		var screenPanels = GameObject.Root.Components.GetAll<ScreenPanel>( FindMode.EverythingInSelfAndDescendants );
		foreach ( var screenPanel in screenPanels )
		{
			if ( screenPanel.IsValid() )
				screenPanel.TargetCamera = camera;
		}
	}

	private EquipmentResource GetInitialEquipment()
	{
		return GunsmithLoadoutManager.GetPrimaryResource()
		       ?? GunsmithLoadoutManager.GetSecondaryResource()
		       ?? Equipment;
	}

	public void SetEquipment( EquipmentResource equipment )
	{
		if ( !equipment.IsValid() )
			return;

		LoadEquipment( equipment );
	}

	public void ApplyPreviewAttachments( EquipmentResource equipment, GunsmithPart previewCamo = null )
	{
		if ( !equipment.IsValid() || !Weapon.IsValid() )
			return;

		var isMp5 = equipment.ResourcePath.Equals( Mp5ResourcePath, System.StringComparison.OrdinalIgnoreCase );
		var stock = isMp5 ? SelectedPartPath( equipment, GunsmithPartType.Stock ) : null;
		if ( isMp5 && !loadingEquipment
			&& !string.Equals( stock, appliedMp5Stock, System.StringComparison.OrdinalIgnoreCase ) )
		{
			// Stock bone overrides survive renderer reparenting. A fresh MP5
			// renderer restores the factory stock when its selection changes.
			LoadEquipment( equipment, previewCamo );
			return;
		}

		GunsmithLoadoutManager.ApplyAttachments( equipment, Weapon.GameObject, previewCamo );
		HidePreviewArms( Weapon.GameObject, Renderer );
		PinPreviewReticles( Weapon.GameObject, equipment );
		appliedMp5Stock = stock;
	}

	/// <summary> How much bigger the reticle is drawn on the preview's lens, so a 1-2% dot is readable. </summary>
	private const float PreviewReticleScale = 3f;

	/// <summary>
	/// The lens shader collimates the reticle: it only lines up when you look straight down the sight, so from the
	/// preview camera it slides off the glass and nothing shows. Pin it to the lens and enlarge it so the chosen shape
	/// and colour can be seen. These are the per-renderer copies ApplyAttachments made, so in-game optics are unchanged.
	/// </summary>
	private static void PinPreviewReticles( GameObject root, EquipmentResource equipment )
	{
		var scale = PreviewReticleScale * GunsmithLoadoutManager.GetCustomReticleScale( equipment );
		foreach ( var renderer in root.Components.GetAll<ModelRenderer>( FindMode.EverythingInSelfAndDescendants ) )
		{
			for ( var i = 0; i < renderer.Materials.Count; i++ )
			{
				if ( !renderer.Materials.HasOverride( i ) )
					continue;

				var material = renderer.Materials.GetOverride( i );
				if ( material is null || material == renderer.Materials.GetOriginal( i )
					|| material.ShaderName?.Contains( "m4_optic_lens" ) != true )
					continue;

				material.Set( "g_flSightDistanceScale", 0f );
				material.Set( "g_flReticleScale", scale );
			}
		}
	}

	private static string SelectedPartPath( EquipmentResource equipment, GunsmithPartType category ) =>
		GunsmithLoadoutManager.TryGetAttachment( equipment, category, out var part ) && part.IsValid()
			? part.ResourcePath : "";

	private static void HidePreviewArms( GameObject root, SkinnedModelRenderer mainRenderer )
	{
		if ( !root.IsValid() )
			return;

		var armsModel = Model.Load( "models/first_person/v_first_person_arms_human.vmdl" );

		foreach ( var renderer in root.Components.GetAll<SkinnedModelRenderer>( FindMode.EverythingInSelfAndDescendants ) )
		{
			if ( !renderer.IsValid() )
				continue;

			if ( renderer != mainRenderer && IsPreviewArmRenderer( renderer, armsModel ) )
			{
				renderer.Enabled = false;
				continue;
			}

			HidePreviewArmMaterialSlots( renderer );
		}
	}

	private static bool IsPreviewArmRenderer( SkinnedModelRenderer renderer, Model armsModel )
	{
		if ( !renderer.IsValid() )
			return false;

		if ( renderer.Model is not null && armsModel is not null && renderer.Model == armsModel )
			return true;

		var matsNullable = renderer.Model?.Materials;
		if ( !matsNullable.HasValue )
			return false;

		return matsNullable.Value.Any( IsPreviewArmMaterial );
	}

	private static void HidePreviewArmMaterialSlots( SkinnedModelRenderer renderer )
	{
		if ( !renderer.IsValid() )
			return;

		var matsNullable = renderer.Model?.Materials;
		if ( !matsNullable.HasValue )
			return;

		var nodraw = Material.Load( "materials/tools/toolsnodraw.vmat" );
		if ( nodraw is null )
			return;

		var mats = matsNullable.Value;
		for ( int i = 0; i < mats.Length; i++ )
		{
			if ( IsPreviewArmMaterial( mats[i] ) )
				renderer.Materials.SetOverride( i, nodraw );
		}
	}

	private static bool IsPreviewArmMaterial( Material material )
	{
		if ( material is null )
			return false;

		var matName = (material.Name?.ToLower() ?? "").Replace( '\\', '/' );
		// Gun parts, not hands. The M16A4's carry handle (m16_carry_handle.vmat) got the nodraw
		// material, which draws on a model as its yellow NODRAW texture instead of hiding it.
		if ( matName.Contains( "handguard" ) || matName.Contains( "handle" ) )
			return false;

		return matName.Contains( "sleeve" )
		       || matName.Contains( "glove" )
		       || matName.Contains( "/hands/" )
		       || matName.Contains( "/arms/" )
		       || matName.Contains( "_hand" )
		       || matName.Contains( "-hand" )
		       || matName.Contains( " hand" )
		       || matName.EndsWith( "hand" )
		       || matName.Contains( "_arm" )
		       || matName.Contains( "-arm" )
		       || matName.Contains( " arm" )
		       || matName.EndsWith( "arm" );
	}

	private static void ApplyGunsmithPreviewModel( EquipmentResource equipment, SkinnedModelRenderer renderer )
	{
		if ( !equipment.IsValid() || !renderer.IsValid() || !IsScarH( equipment ) )
			return;

		var previewModel = Model.Load( ScarHGunsmithModelPath );
		if ( previewModel is null )
		{
			Log.Warning( $"GunsmithSystem: failed to load SCAR-H preview model '{ScarHGunsmithModelPath}'." );
			return;
		}

		renderer.Model = previewModel;
	}

	private static bool IsUnder( GameObject child, GameObject ancestor )
	{
		for ( var go = child; go.IsValid(); go = go.Parent )
		{
			if ( go == ancestor )
				return true;
		}

		return false;
	}

	private static bool IsScarH( EquipmentResource equipment )
	{
		if ( !equipment.IsValid() )
			return false;

		return equipment.ResourcePath.Equals( ScarHResourcePath, System.StringComparison.OrdinalIgnoreCase )
		       || equipment.ResourceName.Equals( ScarHResourcePath, System.StringComparison.OrdinalIgnoreCase )
		       || equipment.ResourcePath.Contains( "scarh", System.StringComparison.OrdinalIgnoreCase )
		       || equipment.ResourceName.Contains( "scarh", System.StringComparison.OrdinalIgnoreCase );
	}

	private void LoadEquipment( EquipmentResource equipment, GunsmithPart previewCamo = null )
	{
		if ( !equipment.IsValid() || !equipment.ViewModelPrefab.IsValid() )
		{
			Log.Error( "GunsmithSystem: Equipment or ViewModelPrefab is missing." );
			return;
		}

		if ( !Controller.IsValid() )
		{
			Log.Error( "GunsmithSystem: Controller reference is missing." );
			return;
		}

		var wasFps = FPS;
		FPS = false;

		if ( Controller.Weapon.IsValid() )
		{
			// First person moves the renderer under the camera, out of a gun whose renderer isn't its root (the 1911).
			if ( Renderer.IsValid() && !IsUnder( Renderer.GameObject, Controller.Weapon.GameObject ) )
				Renderer.GameObject.Destroy();

			Controller.Weapon.GameObject.Destroy();
			Controller.Weapon = null;
		}

		// Only the gun being loaded belongs on the stage. Before SetFirstPerson put the 1911's renderer back in its gun,
		// every 1911 left its model here, drawn over each gun picked after it.
		foreach ( var child in GameObject.Children.ToList() )
		{
			if ( child.Components.Get<SkinnedModelRenderer>( FindMode.EverythingInSelf ).IsValid() )
				child.Destroy();
		}

		Equipment = equipment;
		Renderer = null;

		var inst = equipment.ViewModelPrefab.Clone( new CloneConfig()
		{
			Name = "Runtime Weapon",
			Parent = GameObject,
			StartEnabled = true,
			Transform = new()
		} );

		var weapon = inst.GetComponent<GunsmithWeapon>();
		if ( !weapon.IsValid() )
		{
			weapon = inst.AddComponent<GunsmithWeapon>();
		}

		var viewModel = inst.GetComponent<ViewModel>() ?? inst.GetComponentInChildren<ViewModel>();
		var renderer = viewModel?.ModelRenderer ?? inst.GetComponent<SkinnedModelRenderer>() ?? inst.GetComponentInChildren<SkinnedModelRenderer>();

		weapon.Resource = equipment;
		weapon.ViewModel = viewModel;
		weapon.Renderer = renderer;

		if ( !weapon.IsValid() || !weapon.ViewModel.IsValid() )
		{
			Log.Error( "GunsmithSystem: ViewModelPrefab is missing a valid ViewModel component!" );
			return;
		}

		if ( !weapon.ViewModel.Arms.IsValid() )
			Log.Warning( "GunsmithSystem: ViewModelPrefab is missing an arms reference." );

		Renderer = weapon.Renderer;

		if ( !Renderer.IsValid() )
		{
			Log.Error( "GunsmithSystem: ViewModelPrefab is missing a SkinnedModelRenderer component." );
			return;
		}

		ApplyGunsmithPreviewModel( equipment, Renderer );
		Renderer.UseAnimGraph = false;
		Controller.Weapon = weapon;
		loadingEquipment = true;
		try { ApplyPreviewAttachments( equipment, previewCamo ); }
		finally { loadingEquipment = false; }

		SetFirstPerson( wasFps );
	}
}
