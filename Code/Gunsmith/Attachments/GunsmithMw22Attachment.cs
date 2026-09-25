using System.Collections.Generic;

namespace Facepunch.Gunsmith;

/// <summary>Fits Source attachment origins to the existing M4's animated bind space.</summary>
public sealed class GunsmithMw22Attachment : GunsmithAttachment, ICameraSetup
{
	[Property] public Vector3 BindPosition { get; set; }
	[Property] public Vector3 PartScale { get; set; } = Vector3.One;
	[Property] public Angles PartAngles { get; set; }
	[Property] public string BoneName { get; set; } = "weapon_root";
	[Property] public Dictionary<string, int> BodygroupChoices { get; set; } = new();
	[Property] public Vector3 BarrelMuzzle { get; set; }
	[Property] public Vector3 BarrelFlash { get; set; }
	[Property] public Vector3 BarrelGrip { get; set; }
	[Property] public Vector3 BarrelLaser { get; set; }
	[Property] public bool IsLauncher { get; set; }
	[Property] public Vector3 LaserEmitter { get; set; }
	[Property] public Color LaserColor { get; set; } = new Color( .08f, 1f, .12f );
	[Property] public float LaserWidth { get; set; } = .035f;
	private GunsmithLaserBeam laser;
	private SkinnedModelRenderer weapon;
	private ModelRenderer mesh;
	private GunsmithMw22Factory factory;
	private bool unequipped;

	protected override void OnInitialize()
	{
		unequipped = false;
		weapon = AttachmentPoint?.GetComponentInParent<SkinnedModelRenderer>( true );
		mesh = Components.Get<ModelRenderer>( FindMode.EverythingInSelf );
		if ( !weapon.IsValid() || !mesh.IsValid() ) return;
		foreach ( var choice in BodygroupChoices ) mesh.SetBodyGroup( choice.Key, choice.Value );
		factory = weapon.Components.GetOrCreate<GunsmithMw22Factory>();
		RefreshMount();
		factory.Refresh();
	}

	/// <summary>The weapon takes M4 parts on its own mounts (<see cref="GunsmithAttachmentPoint.MountBone"/>).</summary>
	internal static bool IsRemounted( IEnumerable<GunsmithAttachmentPoint> points ) =>
		points.Any( p => !string.IsNullOrEmpty( p.MountBone ) );

	protected override void OnUpdate() => RefreshMount();

	protected override void OnPreRender() => UpdateLaser();

	// The viewmodel is placed during camera setup, after OnUpdate/OnPreRender; follow it so parts don't trail a frame.
	void ICameraSetup.PostSetup( CameraComponent cc )
	{
		FollowingCamera = true;
		try { RefreshMount(); UpdateLaser(); }
		finally { FollowingCamera = false; }
	}

	private void UpdateLaser()
	{
		if ( !AttachmentPoint.IsValid() || AttachmentPoint.Category != GunsmithPartType.Laser ) return;
		var view = weapon?.Components.Get<ViewModel>( FindMode.EverythingInSelf );
		var owner = view.IsValid() ? view.Equipment?.Owner : weapon?.GetComponentInParent<PlayerPawn>( true );
		var equipment = view.IsValid() ? view.Equipment : owner?.CurrentEquipment;
		var firstPerson = owner.IsValid() && owner.IsViewer && owner.CameraController?.Mode == CameraMode.FirstPerson;
		var heldModel = view.IsValid() ? (WeaponModel)view : equipment?.WorldModel;
		if ( unequipped || !weapon.IsValid() || !weapon.Active || !mesh.Active || !owner.IsValid()
			|| !equipment.IsValid() || !equipment.IsDeployed || owner.CurrentEquipment != equipment
			|| !heldModel.IsValid() || !heldModel.Active || heldModel.ModelRenderer != weapon || firstPerson != view.IsValid() )
		{
			laser?.Hide(); return;
		}
		// Mounting happens in OnUpdate / camera PostSetup; remounting here would read stale bone poses.
		laser ??= Components.GetOrCreate<GunsmithLaserBeam>();
		laser.BeamColor = LaserColor; laser.BeamWidth = LaserWidth;
		laser.TraceBeam( WorldTransform.PointToWorld( LaserEmitter ), WorldRotation.Forward, owner.GameObject );
	}

	protected override void OnDisabled() => laser?.Hide();

	public void RefreshMount()
	{
		if ( unequipped || !weapon.IsValid() || !AttachmentPoint.IsValid() ) return;
		var position = BindPosition;
		var angles = PartAngles;
		var barrel = Find( weapon, GunsmithPartType.Barrel );
		if ( barrel.IsValid() && barrel != this )
		{
			if ( AttachmentPoint.Category == GunsmithPartType.Muzzle ) position = barrel.BarrelMuzzle;
			if ( AttachmentPoint.Category == GunsmithPartType.Underbarrel && !IsLauncher ) position = barrel.BarrelGrip;
			if ( AttachmentPoint.Category == GunsmithPartType.Laser ) { position = barrel.BarrelLaser; angles = new Angles( 0, 0, 90 ); }
		}
		if ( AttachmentPoint.Category == GunsmithPartType.Muzzle ) position += GunsmithAttachmentPoint.MuzzleShift( weapon.GameObject );
		position += AttachmentPoint.MountOffset;
		var pose = BoneDelta( weapon, string.IsNullOrEmpty( AttachmentPoint.MountBone ) ? BoneName : AttachmentPoint.MountBone );
		WorldPosition = pose.PointToWorld( position );
		WorldRotation = pose.Rotation * Rotation.From( angles );
		WorldScale = pose.Scale * PartScale;
		if ( AttachmentPoint.Category == GunsmithPartType.Barrel )
		{
			var points = weapon.Components.GetAll<GunsmithAttachmentPoint>( FindMode.EverythingInSelfAndDescendants );
			var muzzle = points.Any( p => p.Category == GunsmithPartType.Muzzle && p.CurrentPart.IsValid() );
			if ( mesh.Model.Parts.All.Any( p => p.Name == "tag_tip" ) ) mesh.SetBodyGroup( "tag_tip", muzzle ? 1 : 0 );
			// Fold the front sight when an optic is fitted; use the authored off/blank choice.
			var sight = mesh.Model.Parts.All.FirstOrDefault( p => p.Name == "sight" );
			if ( sight is not null ) mesh.SetBodyGroup( "sight", points.Any( p => p.Category == GunsmithPartType.Optic && p.CurrentPart.IsValid() ) ? 1 : 0 );
		}
	}

	internal static GunsmithMw22Attachment Find( SkinnedModelRenderer weapon, GunsmithPartType category )
	{
		var point = weapon.Components.GetAll<GunsmithAttachmentPoint>( FindMode.EverythingInSelfAndDescendants ).FirstOrDefault( p => p.Category == category );
		var mount = point?.CurrentGameObject?.Components.Get<GunsmithMw22Attachment>( FindMode.EverythingInSelf );
		return mount.IsValid() && !mount.unequipped ? mount : null;
	}

	/// <summary>Bone pose relative to its renderer, captured while bones and renderer agree (update phase).</summary>
	private static readonly Dictionary<(SkinnedModelRenderer, string), Transform> boneOffsets = new();
	/// <summary>True while re-mounting after camera setup has moved the viewmodel; bone world transforms are stale then.</summary>
	internal static bool FollowingCamera { get; set; }

	internal static Transform BoneDelta( SkinnedModelRenderer weapon, string bone )
	{
		for ( int i = 0; i < weapon.Model.BoneCount; i++ )
		{
			if ( weapon.Model.GetBoneName( i ) != bone || !weapon.TryGetBoneTransform( bone, out var current ) ) continue;
			var key = (weapon, bone);
			if ( !FollowingCamera )
			{
				if ( boneOffsets.Count > 256 ) foreach ( var dead in boneOffsets.Keys.Where( k => !k.Item1.IsValid() ).ToList() ) boneOffsets.Remove( dead );
				boneOffsets[key] = weapon.WorldTransform.ToLocal( current );
			}
			else if ( boneOffsets.TryGetValue( key, out var offset ) ) current = weapon.WorldTransform.ToWorld( offset );
			var bind = weapon.Model.GetBoneTransform( i );
			return new Transform( current.PointToWorld( bind.PointToLocal( Vector3.Zero ) ), current.Rotation * bind.Rotation.Inverse, current.Scale / bind.Scale );
		}
		return weapon.WorldTransform;
	}

	public override void Unequip()
	{
		unequipped = true;
		laser?.Hide();
		if ( mesh.IsValid() ) mesh.Enabled = false;
		factory?.Refresh();
	}
	protected override void OnDestroy() => Unequip();
}

/// <summary>The original M4's rigid pieces retain their original bones and UVs.</summary>
public sealed class GunsmithMw22Factory : Component, ICameraSetup
{
	private readonly Dictionary<string, ModelRenderer> pieces = new();
	private readonly Dictionary<int, Material> savedMaterials = new();
	private SkinnedModelRenderer weapon;
	private Material hidden;
	private bool replacingWorld;
	private ulong originalBase;
	private ulong savedGasblock;
	private bool hidingGasblock;
	public GameObject MuzzleEffectPoint { get; private set; }

	protected override void OnUpdate() => Refresh();

	void ICameraSetup.PostSetup( CameraComponent cc )
	{
		GunsmithMw22Attachment.FollowingCamera = true;
		try { Refresh(); }
		finally { GunsmithMw22Attachment.FollowingCamera = false; }
	}

	public void Refresh()
	{
		weapon ??= Components.Get<SkinnedModelRenderer>( FindMode.EverythingInSelf );
		if ( !weapon.IsValid() || weapon.Model is null ) return;
		hidden ??= Material.Load( "attachments/m4a1/materials/hidden.vmat" );
		var barrel = GunsmithMw22Attachment.Find( weapon, GunsmithPartType.Barrel ).IsValid();
		var stock = GunsmithMw22Attachment.Find( weapon, GunsmithPartType.Stock ).IsValid();
		var grip = GunsmithMw22Attachment.Find( weapon, GunsmithPartType.RearGrip ).IsValid();
		var muzzle = GunsmithMw22Attachment.Find( weapon, GunsmithPartType.Muzzle ).IsValid();
		var magazine = GunsmithMw22Attachment.Find( weapon, GunsmithPartType.Magazine ).IsValid();
		var world = weapon.Model.BoneCount == 0;
		var points = weapon.Components.GetAll<GunsmithAttachmentPoint>( FindMode.EverythingInSelfAndDescendants );
		// Other weapons fitting the M4's parts have none of its factory pieces to swap in.
		var active = (barrel || stock || grip || muzzle) && !GunsmithMw22Attachment.IsRemounted( points );
		// Any fitted muzzle device (including socket-mounted HC1 parts) replaces the factory flash hider.
		muzzle |= points.Any( p => p.Category == GunsmithPartType.Muzzle && p.CurrentPart.IsValid() );
		if ( world && active ) stock |= points.Any( p => p.Category == GunsmithPartType.Stock && p.CurrentPart.IsValid() );
		if ( active && pieces.Count == 0 )
		{
			foreach ( var bone in world ? new[] { "weapon_root" } : new[] { "weapon_root", "trigger", "bolt" } )
			{
				var name = $"factory_{(world ? "world" : "view")}_{bone}";
				var go = new GameObject( GameObject, true, name );
				go.Flags |= GameObjectFlags.NotSaved | GameObjectFlags.NotNetworked;
				var renderer = go.Components.Create<ModelRenderer>();
				renderer.Model = Model.Load( $"attachments/mw2022/factory/{name}/{name}.vmdl" );
				pieces[bone] = renderer;
			}
		}
		foreach ( var (bone, renderer) in pieces )
		{
			renderer.Enabled = active;
			if ( !active ) continue;
			renderer.WorldTransform = GunsmithMw22Attachment.BoneDelta( weapon, bone );
			renderer.RenderOptions.Game = weapon.RenderOptions.Game;
			renderer.RenderOptions.Overlay = weapon.RenderOptions.Overlay;
			renderer.RenderType = weapon.RenderType;
			renderer.Tint = weapon.Tint;
			foreach ( var (name, hide) in new[] { ("barrel", barrel), ("stock", stock), ("reargrip", grip), ("flashhider", muzzle) } )
				if ( renderer.Model.Parts.All.Any( p => p.Name == name ) ) renderer.SetBodyGroup( name, hide ? 1 : 0 );
		}
		if ( world )
		{
			if ( active && !replacingWorld ) { originalBase = weapon.BodyGroups & 1UL; replacingWorld = true; }
			if ( active ) weapon.BodyGroups &= ~1UL;
			else if ( replacingWorld ) { weapon.BodyGroups = (weapon.BodyGroups & ~1UL) | originalBase; replacingWorld = false; }
			foreach ( var renderer in weapon.Components.GetAll<ModelRenderer>( FindMode.EverythingInSelfAndDescendants ).Where( r => r.Model?.Name == "attachments/m4a1/world_base/world_base.vmdl" ) ) renderer.Enabled = !active;
		}
		else
		{
			SetHidden( "v_m4a1_b.vmat", active );
			SetHidden( "v_m4a1_handguard.vmat", barrel );
			SetHidden( "v_m4a1_stock.vmat", stock );
		}
		var gas = weapon.Model.Parts.All.FirstOrDefault( p => p.Name == "gasblock" );
		if ( gas is not null )
		{
			if ( barrel && !hidingGasblock ) { savedGasblock = weapon.BodyGroups & gas.Mask; hidingGasblock = true; }
			if ( barrel ) weapon.BodyGroups &= ~gas.Mask;
			else if ( hidingGasblock ) { weapon.BodyGroups = (weapon.BodyGroups & ~gas.Mask) | savedGasblock; hidingGasblock = false; }
		}
		if ( magazine )
		{
			var group = weapon.Model.Parts.All.FirstOrDefault( p => p.Name == "magazine" );
			if ( group is not null ) weapon.BodyGroups &= ~group.Mask;
		}
		if ( barrel || muzzle )
		{
			if ( !MuzzleEffectPoint.IsValid() )
			{
				MuzzleEffectPoint = new GameObject( GameObject, true, "MW22 muzzle effects" );
				MuzzleEffectPoint.Flags |= GameObjectFlags.NotSaved | GameObjectFlags.NotNetworked;
			}
			var muzzlePoint = points.FirstOrDefault( p => p.Category == GunsmithPartType.Muzzle );
			var muzzleMesh = muzzlePoint?.CurrentGameObject?.Components.Get<ModelRenderer>( FindMode.EverythingInSelf );
			if ( muzzleMesh.IsValid() )
			{
				MuzzleEffectPoint.WorldPosition = muzzleMesh.WorldTransform.PointToWorld( new Vector3( muzzleMesh.Model.Bounds.Maxs.x, 0, 0 ) );
				MuzzleEffectPoint.WorldRotation = muzzleMesh.WorldRotation;
				MuzzleEffectPoint.WorldScale = weapon.WorldScale;
			}
			else
			{
				var mount = GunsmithMw22Attachment.Find( weapon, GunsmithPartType.Barrel );
				var delta = GunsmithMw22Attachment.BoneDelta( weapon, "weapon_root" );
				MuzzleEffectPoint.WorldTransform = delta.WithPosition( delta.PointToWorld( mount.BarrelFlash ) );
			}
		}
		else if ( MuzzleEffectPoint.IsValid() ) { MuzzleEffectPoint.Destroy(); MuzzleEffectPoint = null; }
	}

	private void SetHidden( string suffix, bool hide )
	{
		var slot = weapon.Model.Materials.ToList().FindIndex( m => m.Name.EndsWith( "/" + suffix ) );
		if ( slot < 0 ) return;
		if ( hide )
		{
			var current = weapon.Materials.GetOverride( slot );
			if ( current != hidden ) savedMaterials[slot] = current;
			weapon.Materials.SetOverride( slot, hidden );
		}
		else if ( savedMaterials.Remove( slot, out var previous ) && weapon.Materials.GetOverride( slot ) == hidden ) weapon.Materials.SetOverride( slot, previous );
	}
}
