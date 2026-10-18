using Facepunch.Gunsmith;
using System;
using System.Collections.Generic;
using System.Linq;

namespace Facepunch;

/// <summary>
/// The first-person gun in a Theater replay (<see cref="TheaterController"/>): the real viewmodel, arms and all, of what
/// the followed soldier has in their hands, in the build it had, where the camera looks out of their eyes. It plays what
/// the replay's actions say they did (<see cref="TheaterReplays.LifeActions"/>): drawing it, firing with its muzzle flash,
/// reloading, aiming down the sights, sprinting and running dry, and it bobs with their walk and swings as they turn, as
/// <see cref="ViewModel"/> does in the game. A replay recorded before there were actions shows the gun in their recorded
/// hand, idle: a player's in the viewer's own saved build, a bot's as it comes.
/// </summary>
public sealed class TheaterViewModel
{
	/// <summary> Longer steps than this through the replay (seeks) don't play what they pass over. </summary>
	const double MaxStep = 0.5;

	/// <summary> Faster than this (u/s) a bot is sprinting: <see cref="LightweightCombatBot"/>'s own line. </summary>
	const float BotSprintSpeed = 190f;

	/// <summary> How long a new or snapped gun animates while the replay is paused, so it takes up its pose. </summary>
	const float SettleTime = 0.35f;

	/// <summary> Seconds a footstep takes (<see cref="PlayerFootsteps.GetStepFrequency"/>): two to a cycle of the walk's bob. </summary>
	const float SprintStep = 0.25f;
	const float CrouchStep = 0.6f;
	const float WalkStep = 0.35f;

	/// <summary> A player's gun in a replay without actions wears the viewer's saved build. </summary>
	const string SavedBuild = "saved";

	GameObject _object;
	ViewModel _viewModel;
	SkinnedModelRenderer _renderer;
	Weapon _weapon;
	string _build;
	GunsmithPart _optic;
	GunsmithPart _rail;

	/// <summary> The SCAR-H, and whether it has an optic's mount fitted (<see cref="ViewModel.IsScarH"/>). </summary>
	bool _scar;
	bool _scarOptic;
	Vector3 _scarSprintPosition;
	Angles _scarSprintAngles;
	float _scarBobTime;

	TheaterClip.Life _life;
	int _held = int.MinValue;
	double _time;
	bool _hasTime;
	RealTimeUntil _settle;

	bool _reloading;
	bool _grounded = true;
	float _nextShell;
	float _lastShell;
	float _aim;
	Vector3 _offset;
	Rotation _angles = Rotation.Identity;
	float _bob;
	float _cycle;
	Angles _lastView;

	readonly Dictionary<GameObject, GameObject> _holds = new();

	/// <summary> Rolls each shot's flash and smoke as the shooter's own machine does. </summary>
	readonly DischargeEffectState _discharge = new();

	/// <summary> What the viewmodel needs from a gun's own prefab: playback has no instance of it. </summary>
	sealed class Weapon
	{
		public EquipmentResource Resource;
		public AnimationHelper.HoldTypes HoldType = AnimationHelper.HoldTypes.Rifle;
		public AnimationHelper.Hand Handedness = AnimationHelper.Hand.Right;
		public float AimFovOffset;
		public GameObject Flash;
		public GameObject SuppressedFlash;
		public float FlashChance;
		public float FlashScale;
		public float SuppressedFlashChance;
		public float SuppressedFlashScale;
		public GameObject Smoke;
		public float SmokeScale;
		public GameObject Ejection;
		public bool BuiltInSuppressor;
		public int FiringMode;
		public bool SingleReload;
		public float ShellTime = 1f;
		public float FirstShellTime = 1f;
		public float ExitTime;
		public ManualOffset Aim;
	}

	static readonly Dictionary<EquipmentResource, Weapon> Weapons = new();
	static readonly Dictionary<Model, EquipmentResource> ByWorldModel = new();
	static bool _worldModelsListed;

	/// <summary>
	/// Shows the gun of <paramref name="life"/> at <paramref name="time"/>, where <paramref name="camera"/> has just been
	/// put in their eyes, and moves the camera as the gun's animation does. <paramref name="rate"/> is how fast the
	/// replay's animations run (0 while paused), and <paramref name="snap"/> puts the gun straight where it's going, as
	/// after a seek. The camera's field of view is <paramref name="baseFov"/>, narrowed while aiming.
	/// </summary>
	public void Update( TheaterClip.Life life, GameObject root, SkinnedModelRenderer body, TheaterReplays.Actions actions,
		CameraComponent camera, double time, float rate, float baseFov, bool snap )
	{
		if ( life != _life )
		{
			Clear();
			_life = life;
		}

		var seconds = (float)time;
		var last = (float)_time;
		var forward = _hasTime && time >= _time && time - _time <= MaxStep;
		var lifeActions = life?.Soldier is { } soldier ? actions?.Lives?.GetValueOrDefault( soldier.Track ?? "" ) : null;

		// What's in their hands: from the actions, else from the gun in their recorded hand.
		var held = -1;
		EquipmentResource resource;
		string build = null;
		var suppressed = false;

		if ( lifeActions is { Held.Count: > 0 } )
		{
			held = lifeActions.HeldAt( seconds );
			var entry = held >= 0 ? lifeActions.Held[held] : null;
			resource = string.IsNullOrEmpty( entry?.Weapon ) ? null : ResourceLibrary.Get<EquipmentResource>( entry.Weapon );
			build = entry is { Build: >= 0 } && entry.Build < (actions.Builds?.Count ?? 0) ? actions.Builds[entry.Build] : null;
			suppressed = entry?.Suppressed ?? false;
		}
		else
		{
			resource = InHand( root );
			if ( lifeActions is null && life?.Soldier is { Bot: false } )
				build = SavedBuild;
		}

		camera.FieldOfView = baseFov;

		if ( !resource.IsValid() || !resource.ViewModelPrefab.IsValid() )
		{
			Remove();
			Advance( held, time );
			return;
		}

		var changed = held != _held;
		if ( !_object.IsValid() || _weapon?.Resource != resource || _build != build )
		{
			Create( GetWeapon( resource ), build, camera );
			changed = true;
		}

		var renderer = _renderer;
		if ( !renderer.IsValid() )
		{
			Advance( held, time );
			return;
		}

		if ( snap )
			_settle = SettleTime;

		// Paused, a new or snapped gun still animates a moment, so it's in its pose rather than its model's.
		var playing = Time.Delta * rate;
		if ( _settle > 0f )
			rate = MathF.Max( rate, 1f );

		var delta = Time.Delta * rate;
		var viewModel = _viewModel;

		// Their state now.
		var aiming = TheaterReplays.LifeActions.IsOn( lifeActions?.Aiming, seconds );
		var reloading = TheaterReplays.LifeActions.IsOn( lifeActions?.Reloading, seconds );
		var empty = TheaterReplays.LifeActions.IsOn( lifeActions?.Empty, seconds );
		var speed = body.IsValid() ? body.GetFloat( "move_groundspeed" ) : 0f;
		var sprinting = lifeActions?.Sprinting is { } sprints ? TheaterReplays.LifeActions.IsOn( sprints, seconds ) : speed > BotSprintSpeed;
		var crouching = body.IsValid() && body.GetFloat( "duck" ) > 0.5f;

		// A body that never had b_grounded set (a bot's) is on the ground.
		var grounded = !body.IsValid() || !body.Parameters.Contains( "b_grounded" ) || body.GetFlag( "b_grounded" );

		// Drawn: a new gun in their hands while the replay plays through it, rather than one found by seeking.
		if ( changed )
		{
			var drawn = forward;
			renderer.SetBool( "b_deploy", drawn );
			renderer.SetBool( "b_deploy_skip", !drawn );

			if ( _scar )
				renderer.SetBool( "deploy", drawn );
		}

		// Aiming down the sights: the viewmodel's own weight, and its weapon's offsets (ManualOffset).
		_aim = snap ? (aiming ? 1f : 0f) : _aim.Approach( aiming ? 1f : 0f, delta / MathF.Max( viewModel?.AimTime ?? 0.25f, 0.01f ) );
		var aimWeight = _aim * _aim * (3f - 2f * _aim);

		var (aimPosition, aimAngles) = aiming ? AimOffset() : (Vector3.Zero, Angles.Zero);
		var blend = snap ? 1f : MathF.Min( delta * 10f, 1f );
		var targetRotation = aimAngles.ToRotation();

		if ( _scar )
			ScarPose( ref aimPosition, ref targetRotation, sprinting && !aiming, speed > 10f && grounded, crouching, blend, playing );

		_offset = _offset.LerpTo( aimPosition, blend );
		_angles = Rotation.Lerp( _angles, targetRotation, blend );

		var view = camera.WorldRotation;
		var rotation = view * _angles;
		_object.WorldRotation = rotation;
		_object.WorldPosition = camera.WorldPosition + rotation * _offset;

		if ( viewModel?.IsThrowable ?? false )
		{
			renderer.SetBool( "b_idle", true );
			renderer.SetBool( "b_pull", false );
			renderer.SetBool( "b_throw", false );
		}
		else
		{
			renderer.SetBool( "b_sprint", sprinting && !aiming );
			renderer.SetBool( "b_grounded", grounded || aiming );
			renderer.Set( "ironsights", aiming ? 1 : 0 );
			renderer.Set( "ironsights_fire_scale", aiming ? viewModel?.IronsightsFireScale ?? 0.2f : 0f );
			renderer.Set( "ironsights_weight", aimWeight );
			renderer.Set( "speed_ironsights", 1 );
			renderer.Set( "reload_speed", viewModel?.ReloadSpeed ?? 1f );
			renderer.SetBool( "b_grab", false );
			renderer.SetBool( "b_lower_weapon", false );
			renderer.Set( "holdtype", (int)_weapon.HoldType );
			renderer.Set( "holdtype_handedness", (int)_weapon.Handedness );
			renderer.SetBool( "b_twohanded", _weapon.HoldType is AnimationHelper.HoldTypes.Rifle or AnimationHelper.HoldTypes.Shotgun );
			renderer.SetBool( "b_empty", empty );
			renderer.Set( "reload_variant", 0 );
			renderer.Set( "firing_mode", _weapon.FiringMode );
		}

		// The walk's bob, stepping at the footsteps' pace.
		var moving = speed > 10f;
		var moveLength = crouching ? speed * 0.5f : speed;
		_bob = _bob.LerpTo( moving && !aiming ? moveLength.Remap( 0f, 300f, 0f, 1f, true ) : 0f, MathF.Min( delta * 10f, 1f ) );
		renderer.Set( "move_bob", _bob * (viewModel?.MoveBobScale ?? 1f) );

		if ( moving && !aiming )
			_cycle = (_cycle + playing / (2f * (sprinting ? SprintStep : crouching ? CrouchStep : WalkStep))) % 1f;
		else
			_cycle = _cycle.LerpTo( 0f, MathF.Min( delta * 4f, 1f ) );

		renderer.Set( "move_bob_cycle_control", _cycle );

		// The gun lags as they turn.
		var angles = view.Angles();
		var pitchInertia = snap ? 0f : Angles.NormalizeAngle( angles.pitch - _lastView.pitch );
		var yawInertia = snap ? 0f : Angles.NormalizeAngle( _lastView.yaw - angles.yaw );
		_lastView = angles;
		renderer.Set( "aim_yaw_inertia", yawInertia * (viewModel?.YawInertiaScale ?? 2f) );
		renderer.Set( "aim_pitch_inertia", pitchInertia * -2f );

		// What they did since the last frame, when the replay played through it.
		if ( forward && lifeActions is not null
			&& TheaterReplays.LifeActions.CountUpTo( lifeActions.Shots, seconds ) > TheaterReplays.LifeActions.CountUpTo( lifeActions.Shots, last ) )
		{
			renderer.SetBool( "b_attack", true );
			if ( _scar )
				renderer.SetBool( aiming ? "fireAimed" : "fire", true );

			Discharge( suppressed );
		}

		UpdateReload( renderer, lifeActions, reloading, empty, forward, seconds );

		if ( forward && _grounded && !grounded && !aiming )
			renderer.SetBool( "b_jump", true );

		_grounded = grounded;

		if ( renderer.SceneModel.IsValid() )
		{
			renderer.SceneModel.PlaybackRate = renderer.PlaybackRate * rate;

			// The animation's camera bone moves the view, as ViewModel's ApplyAnimationTransform does.
			var bone = renderer.SceneModel.GetBoneLocalTransform( "camera" );
			var scale = (GameSettingsSystem.Current?.ViewBob ?? 100f) / 100f;
			camera.WorldPosition += view * (bone.Position * scale);
			camera.WorldRotation = view * (bone.Rotation * scale);
		}

		// Aiming zooms as the game does (Equipment.GetAimFovOffset): a magnified optic further, and by the viewer's
		// ADS Field Of View setting.
		var magnification = Equipment.OffsetMagnification( _weapon.AimFovOffset );
		if ( _optic.IsValid() && _optic.OverrideAimOffset && _optic.OpticMagnification > 1f )
			magnification *= OpticZoom.ViewMagnification;

		var aimFov = Equipment.AimFov( baseFov, magnification ) - baseFov;
		camera.FieldOfView = baseFov + aimFov * aimWeight;

		Advance( held, time );
	}

	void Advance( int held, double time )
	{
		_held = held;
		_time = time;
		_hasTime = true;
	}

	/// <summary>
	/// Starts and stops the reload as Reloadable does: one animation, or a shell at a time for a gun that loads them
	/// singly. Shells aren't recorded, so playback times them as the gun does, until the recorded reload's closing
	/// animation (<see cref="Reloadable.ReloadExitTime"/>).
	/// </summary>
	void UpdateReload( SkinnedModelRenderer renderer, TheaterReplays.LifeActions actions, bool reloading, bool empty, bool forward, float seconds )
	{
		if ( reloading == _reloading )
		{
			if ( reloading && forward && _weapon.SingleReload && _nextShell > 0f )
			{
				if ( seconds >= _lastShell )
				{
					renderer.SetBool( "b_reloading", false );
					_nextShell = 0f;
				}
				else if ( seconds >= _nextShell )
				{
					renderer.SetBool( "b_reloading_shell", true );
					_nextShell += _weapon.ShellTime;
				}
			}

			return;
		}

		_reloading = reloading;
		_nextShell = 0f;

		if ( !reloading )
		{
			renderer.SetBool( "b_reload", false );
			renderer.SetBool( "b_reloading", false );
			return;
		}

		// A reload found by seeking isn't started halfway through.
		if ( !forward )
			return;

		if ( _weapon.SingleReload )
		{
			renderer.SetBool( "b_reloading", true );
			renderer.SetBool( empty ? "b_reloading_first_shell" : "b_reloading_shell", true );

			// The shells stop when the recorded reload does, less the gun coming back up.
			var toggles = actions?.Reloading;
			var count = toggles is null ? 0 : TheaterReplays.LifeActions.CountUpTo( toggles, seconds );
			var stop = toggles is not null && count < toggles.Count ? toggles[count] : float.MaxValue;
			_lastShell = stop - _weapon.ExitTime - 0.05f;
			_nextShell = seconds + (empty ? _weapon.FirstShellTime : _weapon.ShellTime);
		}
		else
		{
			renderer.SetBool( "b_reload", true );
			if ( _scar )
				renderer.SetBool( empty ? "reload_empty" : "reload", true );
		}
	}

	/// <summary>
	/// The SCAR-H's poses its animations don't have, as ViewModel adds them: its sprint pose, and a figure-eight bob as
	/// it walks.
	/// </summary>
	void ScarPose( ref Vector3 position, ref Rotation rotation, bool sprinting, bool walking, bool crouching, float blend, float delta )
	{
		_scarSprintPosition = _scarSprintPosition.LerpTo( sprinting ? ViewModel.ScarHSprintPosition : Vector3.Zero, blend );
		_scarSprintAngles = Angles.Lerp( _scarSprintAngles, sprinting ? ViewModel.ScarHSprintAngles : Angles.Zero, blend );
		position += _scarSprintPosition;
		rotation *= _scarSprintAngles.ToRotation();

		if ( !walking || sprinting )
			return;

		_scarBobTime += delta;
		var bobTime = _scarBobTime * (crouching ? 8f : 12f);
		var bobAmount = crouching ? 0.1f : 0.25f;
		var bobX = MathF.Cos( bobTime ) * bobAmount;
		var bobZ = MathF.Sin( bobTime * 2f ) * bobAmount * 0.5f;

		position += new Vector3( bobX, 0f, bobZ );
		rotation *= new Angles( bobZ * 2f, bobX * 2f, bobX * 2f ).ToRotation();
	}

	/// <summary> The viewmodel's offset while aiming, as the weapon's <see cref="ManualOffset"/> works it out for the fitted optic and rail. </summary>
	(Vector3 Position, Angles Angles) AimOffset()
	{
		var aim = _weapon.Aim;
		if ( !aim.IsValid() )
			return (Vector3.Zero, Angles.Zero);

		if ( _optic.IsValid() && _optic.OverrideAimOffset )
		{
			var line = aim.OpticSightLines?.FirstOrDefault( x => x is not null && x.Optic == _optic );
			var rail = _rail.IsValid() ? _rail.RailOpticAimCorrection : Vector3.Zero;
			return (_optic.OpticAimOffset + aim.OpticAimCorrection + (line?.Position ?? Vector3.Zero) + rail,
				_optic.OpticAimAngles + aim.OpticAngleCorrection( _optic.OpticMagnification ) + (line?.Angles ?? Angles.Zero));
		}

		var (iron, ironAngles) = _scar ? ViewModel.ScarHAimOffset( _scarOptic ) : (aim.AimOffset, aim.AimAngleOffset);
		return (iron + (_rail.IsValid() ? _rail.RailIronAimCorrection : Vector3.Zero), ironAngles);
	}

	/// <summary>
	/// A shot's muzzle flash, smoke and spent case, as Shootable plays them. Whether it flashes or smokes isn't recorded,
	/// so it's rolled as the shooter's machine rolls it. A suppressed shot has its own flash, unless the suppressor is
	/// built in.
	/// </summary>
	void Discharge( bool suppressed )
	{
		var viewModel = _viewModel;
		if ( !viewModel.IsValid() || !viewModel.ModelRenderer.IsValid() )
			return;

		var weapon = _weapon;
		var effects = _discharge.Shoot( suppressed ? weapon.SuppressedFlashChance : weapon.FlashChance,
			suppressed ? weapon.SuppressedFlashScale : weapon.FlashScale, weapon.Smoke.IsValid() ? weapon.SmokeScale : 0f, suppressed );

		var muzzle = viewModel.DischargeMuzzle;
		if ( effects.Flash )
			Particle( suppressed && !weapon.BuiltInSuppressor ? weapon.SuppressedFlash : weapon.Flash, muzzle, effects.FlashScale, "Muzzle flash" );

		if ( effects.SmokeScale > 0f )
			Particle( weapon.Smoke, muzzle, effects.SmokeScale, "Muzzle smoke" );

		viewModel.EjectCasing( weapon.Ejection );
	}

	static void Particle( GameObject prefab, GameObject muzzle, float scale, string name )
	{
		if ( !prefab.IsValid() || !muzzle.IsValid() || scale <= 0f )
			return;

		var particle = prefab.Clone( new CloneConfig { Parent = muzzle, Transform = new Transform().WithScale( scale ), StartEnabled = true, Name = name } );
		if ( particle.IsValid() )
		{
			particle.NetworkMode = NetworkMode.Never;
			particle.Flags |= GameObjectFlags.NotSaved | GameObjectFlags.NotNetworked;
		}
	}

	/// <summary> Makes the viewmodel as Equipment.CreateViewModel does, fitted with <paramref name="build"/>. </summary>
	void Create( Weapon weapon, string build, CameraComponent camera )
	{
		Remove();

		_weapon = weapon;
		_build = build;

		var go = weapon.Resource.ViewModelPrefab.Clone( new CloneConfig
		{
			Name = $"Theater ViewModel ({weapon.Resource.Name})",
			Transform = camera.WorldTransform,
			StartEnabled = true
		} );

		if ( !go.IsValid() )
			return;

		go.Flags |= GameObjectFlags.NotSaved | GameObjectFlags.NotNetworked;

		_object = go;
		_viewModel = go.GetComponentInChildren<ViewModel>( true );
		_renderer = _viewModel?.ModelRenderer ?? go.GetComponentInChildren<SkinnedModelRenderer>( true );

		if ( build == SavedBuild )
			GunsmithLoadoutManager.ApplyAttachments( weapon.Resource, go );
		else if ( build is not null && !GunsmithLoadoutManager.ApplyBuild( weapon.Resource, go, build ) )
			Log.Warning( $"Theater: couldn't fit the recorded build to {weapon.Resource.ResourcePath}." );

		go.BreakFromPrefab();

		var points = go.Components.GetAll<GunsmithAttachmentPoint>( FindMode.EverythingInSelfAndDescendants ).ToList();
		_optic = points.FirstOrDefault( x => x.Category == GunsmithPartType.Optic )?.CurrentPart;
		_rail = points.FirstOrDefault( x => x.Category == GunsmithPartType.Rail )?.CurrentPart;

		_scar = ViewModel.IsScarH( weapon.Resource );
		_scarOptic = points.Any( x => x.Category == GunsmithPartType.Optic && x.CurrentPart.IsValid() && x.CurrentPart.ModifyBodygroups );
		_scarSprintPosition = Vector3.Zero;
		_scarSprintAngles = Angles.Zero;

		_reloading = false;
		_nextShell = 0f;
		_grounded = true;
		_aim = 0f;
		_offset = Vector3.Zero;
		_angles = Rotation.Identity;
		_bob = 0f;
		_cycle = 0f;
		_lastView = camera.WorldRotation.Angles();
		_settle = SettleTime;
	}

	/// <summary> Takes the gun away, until there's one in their hands again. </summary>
	void Remove()
	{
		if ( _object.IsValid() )
			_object.Destroy();

		_object = null;
		_viewModel = null;
		_renderer = null;
		_weapon = null;
		_build = null;
		_optic = null;
		_rail = null;
	}

	/// <summary> Out of first person: takes the gun away and forgets whom it was for. </summary>
	public void Clear()
	{
		Remove();
		_life = null;
		_held = int.MinValue;
		_hasTime = false;
	}

	/// <summary> The gun in the soldier's recorded hand, for a replay without actions: the world model on their hold. </summary>
	EquipmentResource InHand( GameObject root )
	{
		if ( !root.IsValid() )
			return null;

		// A player's hold is WeaponHold on their hand, a bot's is WeaponHold on the bot, and a player in an old uniform
		// holds it on the model's hold_R bone.
		if ( !_holds.TryGetValue( root, out var hold ) )
		{
			hold = Find( root, x => x.Name == "WeaponHold" )
				?? Find( root, x => x.Name.Equals( "hold_R", StringComparison.OrdinalIgnoreCase ) );
			_holds[root] = hold;
		}

		if ( !hold.IsValid() || !hold.Active )
			return null;

		foreach ( var child in hold.Children )
		{
			if ( !child.Active )
				continue;

			foreach ( var renderer in child.GetComponentsInChildren<ModelRenderer>() )
			{
				if ( FromWorldModel( renderer.Model ) is { } resource )
					return resource;
			}
		}

		return null;
	}

	static GameObject Find( GameObject parent, Func<GameObject, bool> match )
	{
		foreach ( var child in parent.Children )
		{
			if ( match( child ) )
				return child;

			if ( Find( child, match ) is { } found )
				return found;
		}

		return null;
	}

	/// <summary> The weapon whose world model is <paramref name="model"/>. </summary>
	static EquipmentResource FromWorldModel( Model model )
	{
		if ( model is null )
			return null;

		if ( !_worldModelsListed )
		{
			_worldModelsListed = true;

			foreach ( var resource in ResourceLibrary.GetAll<EquipmentResource>() )
			{
				if ( !resource.ViewModelPrefab.IsValid() || !resource.WorldModelPrefab.IsValid()
					|| GunsmithLoadoutManager.IsMergedWeaponResource( resource ) )
					continue;

				if ( resource.WorldModelPrefab.GetComponentInChildren<ModelRenderer>( true )?.Model is { } worldModel )
					ByWorldModel.TryAdd( worldModel, resource );
			}
		}

		return ByWorldModel.GetValueOrDefault( model );
	}

	static Weapon GetWeapon( EquipmentResource resource )
	{
		if ( Weapons.TryGetValue( resource, out var weapon ) )
			return weapon;

		weapon = new Weapon { Resource = resource };
		var prefab = resource.MainPrefab;

		if ( prefab.IsValid() )
		{
			if ( prefab.GetComponentInChildren<Equipment>( true ) is { } equipment )
			{
				weapon.HoldType = equipment.GetHoldType();
				weapon.Handedness = equipment.GetHandedness();
				weapon.AimFovOffset = equipment.AimFovOffset;
			}

			if ( prefab.GetComponentInChildren<Shootable>( true ) is { } shootable )
			{
				weapon.Flash = shootable.MuzzleFlashPrefab;
				weapon.SuppressedFlash = shootable.SuppressedMuzzleFlashPrefab;
				weapon.FlashChance = shootable.MuzzleFlashChance;
				weapon.FlashScale = shootable.MuzzleFlashScale;
				weapon.SuppressedFlashChance = shootable.SuppressedMuzzleFlashChance;
				weapon.SuppressedFlashScale = shootable.SuppressedMuzzleFlashScale;
				weapon.Smoke = shootable.MuzzleSmokePrefab;
				weapon.SmokeScale = shootable.MuzzleSmokeScale;
				weapon.Ejection = shootable.EjectionPrefab;
				weapon.BuiltInSuppressor = shootable.HasBuiltInSuppressor;

				// As ViewModel.OnFireMode numbers them: the gun's own mode, as which one was picked isn't recorded.
				weapon.FiringMode = shootable.CurrentFireMode switch
				{
					FireMode.Semi => 1,
					FireMode.Burst => 2,
					FireMode.Automatic => 3,
					_ => 0
				};
			}

			if ( prefab.GetComponentInChildren<Reloadable>( true ) is { } reloadable )
			{
				weapon.SingleReload = reloadable.SingleReload;
				weapon.ShellTime = MathF.Max( reloadable.ReloadTime, 0.1f );
				weapon.FirstShellTime = MathF.Max( reloadable.EmptyReloadTime, 0.1f );
				weapon.ExitTime = reloadable.ReloadExitTime;
			}

			weapon.Aim = prefab.GetComponentInChildren<ManualOffset>( true );
		}

		Weapons[resource] = weapon;
		return weapon;
	}
}
