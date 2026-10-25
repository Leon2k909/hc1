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
	/// <summary> No longer read: the beam's width is the real one (<see cref="GunsmithLaserBeam"/>). Kept for the prefabs. </summary>
	[Property, Hide] public float LaserWidth { get; set; } = .035f;
	private GunsmithLaserBeam laser;
	// Made on first use: a hotload leaves new fields of a live component unset.
	private ScopeEyeAlignment laserSight;
	private ScopeEyeMotion laserEyeMotion;

	/// <summary>
	/// Where a laser's beam crosses the sights' line: 25 m, the range soldiers zero an aiming laser at. Nearer, its spot
	/// sits a little off the sights on the laser's side of the gun; further, across on the other side.
	/// </summary>
	public const float LaserZeroMetres = 25f;

	/// <summary>
	/// Each gun's line of sight in a laser's own frame, learned while it was aimed, by the gun, the laser and the optic:
	/// a laser drawn again (a new life, the gun swapped back) is zeroed from its first frame.
	/// </summary>
	private static readonly Dictionary<string, (Vector3 Eye, Rotation Aim)> LaserZeros = new();
	private SkinnedModelRenderer weapon;
	private ModelRenderer mesh;
	private GunsmithMw22Factory factory;
	private bool unequipped;
	private bool? followsCamera;
	private Model partsModel;
	private bool hasTip, hasSight;

	protected override void OnInitialize()
	{
		unequipped = false;
		followsCamera = null;
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
		if ( !(followsCamera ??= OnViewModel( weapon )) ) return;
		FollowingCamera = true;
		try { RefreshMount(); }
		finally { FollowingCamera = false; }
	}

	/// <summary>
	/// Whether <paramref name="weapon"/> is a viewmodel: camera setup moves only those, after the update. A world model's
	/// parts are its children, so they move with it, and mounting them again then gives the place they already have.
	/// </summary>
	internal static bool OnViewModel( SkinnedModelRenderer weapon ) =>
		weapon.IsValid() && weapon.GetComponentInParent<ViewModel>( true ).IsValid();

	void ICameraSetup.LateSetup( CameraComponent cc ) => UpdateLaser( cc );

	private void UpdateLaser( CameraComponent camera = null )
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
		// The first-person emitter and aim ray must both use the final camera setup. OnPreRender
		// only handles world models, so its ordering cannot overwrite the viewmodel's finished beam.
		if ( view.IsValid() )
		{
			if ( !camera.IsValid() || camera != owner.CameraController?.Camera ) return;
		}
		else if ( camera.IsValid() ) return;

		// A laser is fixed to the gun and zeroed to its sights, so it points wherever the gun does: through sway, recoil,
		// a reload or the hip. Only a viewmodel has the sights' line (the camera's, once it's aimed); a gun in someone's
		// hands points its laser along its rail.
		var emitter = WorldTransform.PointToWorld( LaserEmitter );
		var direction = WorldRotation.Forward;
		if ( view.IsValid() && LaserSightLine( view, equipment, camera ) is { } sight )
		{
			var zero = sight.Eye + sight.Forward * LaserZeroMetres * LaserOptics.UnitsPerMetre;
			if ( Vector3.Dot( zero - emitter, direction ) > 0f ) direction = (zero - emitter).Normal;
		}

		// Mounting happens in OnUpdate / camera PostSetup; remounting here would read stale bone poses.
		laser ??= Components.GetOrCreate<GunsmithLaserBeam>();
		laser.BeamColor = LaserColor;
		laser.TraceBeam( emitter, direction, owner.GameObject, view.IsValid() ? camera : null );
	}

	/// <summary>
	/// The sights' line in the world now, from where it lies in this laser's frame: learned (as the magnified optics learn
	/// their eye, <see cref="ScopeEyeAlignment"/>) once the gun has been aimed and held still, so it's the line the sights
	/// really show, and carried with the gun from then on.
	/// </summary>
	private (Vector3 Eye, Vector3 Forward)? LaserSightLine( ViewModel view, Equipment equipment, CameraComponent camera )
	{
		laserSight ??= new ScopeEyeAlignment();
		laserEyeMotion ??= new ScopeEyeMotion();
		var part = WorldTransform;
		var eye = camera.WorldTransform;
		var motion = laserEyeMotion.Update( eye.Rotation, Time.Delta );
		var aimed = view.IsAimSettled && !view.IsInspecting && !equipment.HasTag( "reloading" );
		laserSight.Update( eye, part, Rotation.FromRoll( view.CornerRoll ), 0f, 1f, aimed,
			laserEyeMotion.TurnSpeed < 15f && motion.Length < 0.015f, Time.Delta );

		var key = LaserZeroKey();
		if ( laserSight.Calibrated ) LaserZeros[key] = (laserSight.NeutralEyeLocal, laserSight.AimLocal);
		if ( !LaserZeros.TryGetValue( key, out var learned ) ) return null;
		return (part.PointToWorld( learned.Eye ), (part.Rotation * learned.Aim).Forward);
	}

	private string LaserZeroKey()
	{
		var optic = GunsmithAttachmentPoint.First( weapon.GameObject, GunsmithPartType.Optic )?.CurrentPart;
		return $"{weapon.Model?.ResourcePath}|{GameObject.Name}|{optic?.ResourcePath}";
	}

	protected override void OnDisabled() => laser?.Hide();

	public void RefreshMount()
	{
		if ( unequipped || !weapon.IsValid() || !AttachmentPoint.IsValid() ) return;
		var position = BindPosition;
		var angles = PartAngles;
		var offset = AttachmentPoint.MountOffset;
		var barrel = Find( weapon, GunsmithPartType.Barrel );
		if ( barrel.IsValid() && barrel != this )
		{
			// These positions are authored in the barrel's bind space, including its weapon-specific offset.
			if ( AttachmentPoint.Category == GunsmithPartType.Muzzle ) { position = barrel.BarrelMuzzle; offset = barrel.AttachmentPoint.MountOffset; }
			if ( AttachmentPoint.Category == GunsmithPartType.Underbarrel && !IsLauncher ) { position = barrel.BarrelGrip; offset = barrel.AttachmentPoint.MountOffset; }
			if ( AttachmentPoint.Category == GunsmithPartType.Laser ) { position = barrel.BarrelLaser; offset = barrel.AttachmentPoint.MountOffset; angles = new Angles( 0, 0, 90 ); }
		}
		if ( AttachmentPoint.Category == GunsmithPartType.Muzzle ) position += GunsmithAttachmentPoint.MuzzleShift( weapon.GameObject );
		if ( AttachmentPoint.Category == GunsmithPartType.Optic )
		{
			var mountShift = Vector3.Zero;
			foreach ( var point in GunsmithAttachmentPoint.On( weapon.GameObject ) )
				if ( point.CurrentPart.IsValid() ) mountShift += point.CurrentPart.OpticMountShift;
			position += mountShift;
			// Its tuned Eye Position: a slide along the rail, which runs with the bore (+x in bind space).
			position += Vector3.Forward * AttachmentPoint.OpticRailShift;
		}
		position += offset;
		var pose = BoneDelta( weapon, string.IsNullOrEmpty( AttachmentPoint.MountBone ) ? BoneName : AttachmentPoint.MountBone );
		WorldPosition = pose.PointToWorld( position );
		WorldRotation = pose.Rotation * Rotation.From( angles );
		WorldScale = pose.Scale * PartScale;
		if ( AttachmentPoint.Category == GunsmithPartType.Barrel )
		{
			var muzzle = false;
			var optic = false;
			foreach ( var point in GunsmithAttachmentPoint.On( weapon.GameObject ) )
			{
				muzzle |= point.Category == GunsmithPartType.Muzzle && point.CurrentPart.IsValid();
				optic |= point.Category == GunsmithPartType.Optic && point.CurrentPart.IsValid();
			}
			if ( partsModel != mesh.Model )
			{
				partsModel = mesh.Model;
				hasTip = partsModel.Parts.All.Any( p => p.Name == "tag_tip" );
				hasSight = partsModel.Parts.All.Any( p => p.Name == "sight" );
			}
			if ( hasTip ) mesh.SetBodyGroup( "tag_tip", muzzle ? 1 : 0 );
			// Fold the front sight when an optic is fitted; use the authored off/blank choice.
			if ( hasSight ) mesh.SetBodyGroup( "sight", optic ? 1 : 0 );
		}
	}

	internal static GunsmithMw22Attachment Find( SkinnedModelRenderer weapon, GunsmithPartType category )
	{
		var point = GunsmithAttachmentPoint.First( weapon.GameObject, category );
		var mount = point?.CurrentGameObject?.Components.Get<GunsmithMw22Attachment>( FindMode.EverythingInSelf );
		return mount.IsValid() && !mount.unequipped ? mount : null;
	}

	/// <summary>True while re-mounting after camera setup; socket attachments use their cached model-space offset.</summary>
	internal static bool FollowingCamera { get; set; }

	/// <summary> Each model's bones by name: every part on every gun asks twice a frame, and a bone's name is a native call. </summary>
	private static readonly Dictionary<(BoneCollection, string), BoneCollection.Bone> boneLookup = new();

	internal static Transform BoneDelta( SkinnedModelRenderer weapon, string bone )
	{
		var bones = weapon.Model.Bones;
		if ( !boneLookup.TryGetValue( (bones, bone), out var found ) )
			boneLookup[(bones, bone)] = found = bone is null ? null : bones.GetBone( bone );
		if ( found is null )
			return weapon.WorldTransform;

		Transform current;
		var model = weapon.SceneModel;
		if ( model.IsValid() )
		{
			// Animation and camera setup can run after OnUpdate, and the SceneModel can still be in last frame's space.
			// Read this pose in its own render space, then carry it into the gun's current space. An update-phase cache
			// either misses the latest sprint pose or mixes the renderer's old transform with the gun's new one.
			var local = model.Transform.ToLocal( model.GetBoneWorldTransform( found.Index ) );
			current = weapon.WorldTransform.ToWorld( local );
		}
		else if ( !weapon.TryGetBoneTransform( found, out current ) )
			return weapon.WorldTransform;
		var bind = weapon.Model.GetBoneTransform( found.Index );
		return new Transform( current.PointToWorld( bind.PointToLocal( Vector3.Zero ) ), current.Rotation * bind.Rotation.Inverse, current.Scale / bind.Scale );
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
		weapon ??= Components.Get<SkinnedModelRenderer>( FindMode.EverythingInSelf );
		if ( !(followsCamera ??= GunsmithMw22Attachment.OnViewModel( weapon )) ) return;
		GunsmithMw22Attachment.FollowingCamera = true;
		try { Refresh(); }
		finally { GunsmithMw22Attachment.FollowingCamera = false; }
	}

	private bool? followsCamera;
	/// <summary> What Refresh looks up by name on the weapon's model and the pieces' models, found once per model. </summary>
	private Model namedModel;
	private readonly Dictionary<string, int> materialSlots = new();
	private Model.BodyPart gasPart, magazinePart;
	private readonly Dictionary<ModelRenderer, (Model Model, bool[] Groups)> pieceGroups = new();
	private static readonly string[] PieceGroups = { "barrel", "stock", "reargrip", "flashhider" };
	private (int Version, ModelRenderer[] Renderers) worldBase = (-1, null);

	public void Refresh()
	{
		weapon ??= Components.Get<SkinnedModelRenderer>( FindMode.EverythingInSelf );
		if ( !weapon.IsValid() || weapon.Model is null ) return;
		hidden ??= Material.Load( "attachments/m4a1/materials/hidden.vmat" );
		if ( namedModel != weapon.Model )
		{
			namedModel = weapon.Model;
			materialSlots.Clear();
			gasPart = namedModel.Parts.All.FirstOrDefault( p => p.Name == "gasblock" );
			magazinePart = namedModel.Parts.All.FirstOrDefault( p => p.Name == "magazine" );
		}
		var barrel = GunsmithMw22Attachment.Find( weapon, GunsmithPartType.Barrel ).IsValid();
		var stock = GunsmithMw22Attachment.Find( weapon, GunsmithPartType.Stock ).IsValid();
		var grip = GunsmithMw22Attachment.Find( weapon, GunsmithPartType.RearGrip ).IsValid();
		var muzzle = GunsmithMw22Attachment.Find( weapon, GunsmithPartType.Muzzle ).IsValid();
		var magazine = GunsmithMw22Attachment.Find( weapon, GunsmithPartType.Magazine ).IsValid();
		var world = weapon.Model.BoneCount == 0;
		var points = GunsmithAttachmentPoint.On( weapon.GameObject );
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
			if ( !pieceGroups.TryGetValue( renderer, out var groups ) || groups.Model != renderer.Model )
				pieceGroups[renderer] = groups = (renderer.Model,
					PieceGroups.Select( name => renderer.Model.Parts.All.Any( p => p.Name == name ) ).ToArray());
			if ( groups.Groups[0] ) renderer.SetBodyGroup( "barrel", barrel ? 1 : 0 );
			if ( groups.Groups[1] ) renderer.SetBodyGroup( "stock", stock ? 1 : 0 );
			if ( groups.Groups[2] ) renderer.SetBodyGroup( "reargrip", grip ? 1 : 0 );
			if ( groups.Groups[3] ) renderer.SetBodyGroup( "flashhider", muzzle ? 1 : 0 );
		}
		if ( world )
		{
			if ( active && !replacingWorld ) { originalBase = weapon.BodyGroups & 1UL; replacingWorld = true; }
			if ( active ) weapon.BodyGroups &= ~1UL;
			else if ( replacingWorld ) { weapon.BodyGroups = (weapon.BodyGroups & ~1UL) | originalBase; replacingWorld = false; }
			// The world base meshes are parts' renderers, so the list only changes with the points.
			if ( worldBase.Version != GunsmithAttachmentPoint.Version || worldBase.Renderers.Any( r => !r.IsValid() ) )
				worldBase = (GunsmithAttachmentPoint.Version, weapon.Components.GetAll<ModelRenderer>( FindMode.EverythingInSelfAndDescendants )
					.Where( r => r.Model?.Name == "attachments/m4a1/world_base/world_base.vmdl" ).ToArray());
			foreach ( var renderer in worldBase.Renderers ) renderer.Enabled = !active;
		}
		else
		{
			SetHidden( "v_m4a1_b.vmat", active );
			SetHidden( "v_m4a1_handguard.vmat", barrel );
			SetHidden( "v_m4a1_stock.vmat", stock );
		}
		var gas = gasPart;
		if ( gas is not null )
		{
			if ( barrel && !hidingGasblock ) { savedGasblock = weapon.BodyGroups & gas.Mask; hidingGasblock = true; }
			if ( barrel ) weapon.BodyGroups &= ~gas.Mask;
			else if ( hidingGasblock ) { weapon.BodyGroups = (weapon.BodyGroups & ~gas.Mask) | savedGasblock; hidingGasblock = false; }
		}
		if ( magazine )
		{
			var group = magazinePart;
			if ( group is not null ) weapon.BodyGroups &= ~group.Mask;
		}
		if ( barrel || muzzle )
		{
			if ( !MuzzleEffectPoint.IsValid() )
			{
				MuzzleEffectPoint = new GameObject( GameObject, true, "MW22 muzzle effects" );
				MuzzleEffectPoint.Flags |= GameObjectFlags.NotSaved | GameObjectFlags.NotNetworked;
			}
			var muzzlePoint = GunsmithAttachmentPoint.First( weapon.GameObject, GunsmithPartType.Muzzle );
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
				var point = mount.AttachmentPoint;
				var delta = GunsmithMw22Attachment.BoneDelta( weapon, string.IsNullOrEmpty( point.MountBone ) ? mount.BoneName : point.MountBone );
				MuzzleEffectPoint.WorldTransform = delta.WithPosition( delta.PointToWorld( mount.BarrelFlash + point.MountOffset ) );
			}
		}
		else if ( MuzzleEffectPoint.IsValid() ) { MuzzleEffectPoint.Destroy(); MuzzleEffectPoint = null; }
	}

	private void SetHidden( string suffix, bool hide )
	{
		if ( !materialSlots.TryGetValue( suffix, out var slot ) )
			materialSlots[suffix] = slot = weapon.Model.Materials.ToList().FindIndex( m => m.Name.EndsWith( "/" + suffix ) );
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
