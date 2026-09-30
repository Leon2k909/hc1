using Sandbox.Diagnostics;
using Sandbox.Events;

namespace Facepunch;

/// <summary>
/// A cheap FPS-style combat bot that participates in HC1 teams without becoming a full Client/PlayerPawn.
/// </summary>
public sealed partial class LightweightCombatBot : Component, ITeam, IDescription, IRespawnable, IAreaDamageReceiver, IMarkerObject,
	IGameEventHandler<KillEvent>,
	IGameEventHandler<ResetScoresEvent>,
	IGameEventHandler<DamageTakenEvent>
{
	[Property] public Team Team { get; set; } = Team.Unassigned;
	[Property] public string BotName { get; set; } = "Raven";
	[Property] public HealthComponent HealthComponent { get; set; }
	[Property] public NavMeshAgent Agent { get; set; }
	[Property] public SkinnedModelRenderer Renderer { get; set; }

	[Property, Group( "Combat" )] public float SightRange { get; set; } = 6000f;
	/// <summary> Beyond this the bot holds fire: at that distance a soldier is spotting, not shooting. </summary>
	[Property, Group( "Combat" )] public float EngageRange { get; set; } = 4000f;
	/// <summary> The distance bots like to fight at; aggressive ones get closer, cautious ones hang back. </summary>
	[Property, Group( "Combat" )] public float PreferredRange { get; set; } = 550f;
	/// <summary>
	/// Fallback damage per round, used when the gun has no Shootable; otherwise it's the gun's BaseDamage after falloff.
	/// Hardcore decides it by hit location (HealthComponent.Wounds.cs).
	/// </summary>
	[Property, Group( "Combat" )] public float Damage { get; set; } = 20f;
	[Property, Group( "Combat" )] public float RealPlayerDamageScale { get; set; } = 0.75f;
	/// <summary>Whether this bot's weapon is loaded with tracer rounds. Ordinary ammo has no visible trail.</summary>
	[Property, Group( "Combat" )] public bool UsesTracerRounds { get; set; } = false;
	[Property, Group( "Movement" )] public float MoveSpeed { get; set; } = 230f;
	/// <summary>
	/// How fast the bot's velocity can change, in units/s², set on the NavMeshAgent at spawn. The agent steers straight at
	/// the route's next corner and changes velocity no faster than this, so it sets how quickly a bot cuts a corner or
	/// changes course. The prefab's 250 took 1.3 s to turn 90 degrees and 1.8 s to turn back, slowing to a crawl in the
	/// middle, which looked like the bot drifting round. At 800 a run turns 90 degrees in 0.4 s and starts from still in
	/// 0.3 s, a person planting a foot; the player's own movement is quicker still.
	/// </summary>
	[Property, Group( "Movement" )] public float MoveAcceleration { get; set; } = 800f;
	[Property, Group( "Movement" )] public float PatrolRadius { get; set; } = 900f;
	[Property, Group( "Visuals" ), InlineEditor] public Dictionary<Team, HumanOutfitter.TeamModelEntry> TeamBaseModels { get; set; } = new();
	/// <summary> Fallback world model, used when <see cref="WeaponResource"/> has none. </summary>
	[Property, Group( "Visuals" )] public string WeaponWorldModelPrefab { get; set; } = "weapons/m4a1/wm_m4a1.prefab";
	/// <summary>
	/// The bot's gun. Its world model, damage and falloff, fire rate, magazine, reload times, shot sound and muzzle flash
	/// all come from the gun's own prefabs, so a bot fights with the real gun's numbers. The bot manager issues one per
	/// soldier (<see cref="RollWeapon"/>) and sets it before the bot is networked, so every client sees the same gun.
	/// </summary>
	[Property, Group( "Combat" )] public EquipmentResource WeaponResource { get; set; } = ResourceLibrary.Get<EquipmentResource>( "weapons/m4a1/m4a1.equip" );
	/// <summary>
	/// The suppressor on the bot's gun, if it was issued one (<see cref="RollMuzzle"/>). Set with the gun, before the bot is
	/// networked, so every client fits the same one to the world model.
	/// </summary>
	[Property, Group( "Combat" )] public Gunsmith.GunsmithPart MuzzlePart { get; set; }

	/// <summary> A suppressed gun: the gun's suppressed shot, heard only close by, and hardly any flash. </summary>
	public bool IsSuppressed => MuzzlePart.IsValid() && MuzzlePart.IsSuppressor;
	/// <summary> Fallback muzzle flash, used when the gun's Shootable has none. </summary>
	[Property, Group( "Effects" )] public string MuzzleFlashPrefab { get; set; } = "prefabs/weapon_effects/rifle_muzzleflash.prefab";
	[Property, Group( "Effects" )] public GameObject BloodEffect { get; set; }
	[Property, Group( "Effects" )] public string TracerEffectPrefab { get; set; } = "weapons/common/effects/tracer_9mm.prefab";
	/// <summary> Fallback shot sound, used when the gun's Shootable has none. </summary>
	[Property, Group( "Effects" )] public string ShootSound { get; set; } = "sounds/weapons/m4a1/m4_shot.sound";

	public bool IsAlive => HealthComponent.IsValid() && HealthComponent.State == LifeState.Alive;
	public Vector3 EyePosition => WorldPosition + Vector3.Up * (IsCrouching ? 44f : 64f);

	[Sync( SyncFlags.FromHost ), Property, ReadOnly] public int Kills { get; private set; }
	[Sync( SyncFlags.FromHost ), Property, ReadOnly] public int Deaths { get; private set; }
	[Sync( SyncFlags.FromHost ), Property, ReadOnly] public int Score { get; private set; }
	public float Ratio => (float)Kills / (float)Deaths.Clamp( 1, int.MaxValue );

	string IDescription.DisplayName => $"{BotName} BOT";
	Color IDescription.Color => Team.GetColor();
	Type IMarkerObject.MarkerPanelTypeOverride => typeof( UI.LightweightBotMarkerPanel );
	Vector3 IMarkerObject.MarkerPosition => WorldPosition + Vector3.Up * 78f;
	bool IMarkerObject.ShowChevron => false;

	bool IMarkerObject.ShouldShow()
	{
		var viewer = Client.Viewer?.PlayerPawn;
		return IsAlive && Team != Team.Unassigned && viewer.IsValid() && viewer.Team == Team;
	}

	private GameObject _weaponModel;
	private GameObject _weaponHold;
	private bool _dying;

	private const int KillScore = 25;
	private const int TeamKillScore = -25;
	private const int SuicideScore = -10;
	private const float TargetMemorySeconds = 8f;
	private const float CorpseLifetime = 15f;

	protected override void OnStart()
	{
		EnsureReferences();
		ConfigureComponents();
		AttachWeaponModel();
		AttachMovementBox();

		if ( RandomizePersonality && !IsProxy )
			RollPersonality();
	}

	protected override void OnUpdate()
	{
		var timer = FastTimer.StartNew();
		UpdateBot();
		BotSystem.Current?.AddBotTime( timer.ElapsedMicroSeconds );
	}

	private void UpdateBot()
	{
		EnsureReferences();
		AttachWeaponModel();
		AttachMovementBox();
		UpdateAnimation();

		if ( IsProxy )
			return;

		if ( Networking.IsActive && !Networking.IsHost )
			return;

		if ( !IsAlive )
			return;

		if ( GameUtils.IsCombatFrozen )
		{
			ResetCombatState();
			return;
		}

		var thinkTimer = FastTimer.StartNew();
		Think();
		BotSystem.Current?.AddThinkTime( thinkTimer.ElapsedMicroSeconds );
	}

	private void EnsureReferences()
	{
		HealthComponent ??= Components.Get<HealthComponent>();
		Agent ??= Components.Get<NavMeshAgent>();
		Renderer ??= Components.GetInChildren<SkinnedModelRenderer>( true );
	}

	internal void ApplyTeamModel()
	{
		EnsureReferences();
		if ( !Renderer.IsValid() )
			return;

		// Match the player outfitter, including its T-side fallback for free-for-all.
		if ( !TeamBaseModels.TryGetValue( Team, out var entry )
			&& !TeamBaseModels.TryGetValue( Team.Terrorist, out entry ) )
			return;

		if ( entry.Models is { Count: > 0 } )
			MilitaryUniform.SetModel( Renderer, Game.Random.FromList( entry.Models ), MilitaryUniform.StyleForTeam( Team ) );
	}

	private void ConfigureComponents()
	{
		GameObject.Tags.Add( LightweightBotManager.BotTag );
		GameObject.Tags.Add( "player" );

		if ( HealthComponent.IsValid() )
		{
			HealthComponent.Health = HealthComponent.MaxHealth;
		}

		if ( Agent.IsValid() )
		{
			Agent.MaxSpeed = MoveSpeed;
			Agent.Acceleration = MoveAcceleration;
			Agent.Radius = MathF.Max( Agent.Radius, 24f );
			Agent.Height = MathF.Max( Agent.Height, 64f );
			Agent.Separation = MathF.Max( Agent.Separation, 1.25f );
			Agent.UpdateRotation = false;
			Agent.UpdatePosition = true;
		}
	}

	private void AttachWeaponModel()
	{
		if ( _dying || _weaponModel.IsValid() )
			return;

		var prefab = WeaponResource?.WorldModelPrefab;
		if ( !prefab.IsValid() && !string.IsNullOrWhiteSpace( WeaponWorldModelPrefab ) )
			prefab = GameObject.GetPrefab( WeaponWorldModelPrefab );
		if ( !prefab.IsValid() )
			return;

		var parent = GetWeaponHold();
		if ( !parent.IsValid() )
			return;

		_weaponModel = prefab.Clone( new CloneConfig
		{
			Name = WeaponResource?.Name ?? "Weapon",
			Parent = parent,
			StartEnabled = true
		} );

		if ( !_weaponModel.IsValid() )
			return;

		_weaponModel.Flags |= GameObjectFlags.NotSaved | GameObjectFlags.NotNetworked;
		// The factory gun, as a player's world model shows it (Equipment.CreateWorldModel).
		if ( _weaponModel.Components.TryGet<SkinnedModelRenderer>( out var renderer, FindMode.EverythingInSelfAndDescendants ) )
		{
			renderer.SetBodyGroup( "sight", 0 );
			renderer.SetBodyGroup( "muzzle", 0 );
		}

		// Its suppressor, fitted as the gunsmith fits a player's, with nothing from this machine's own loadout.
		if ( IsSuppressed && WeaponResource.IsValid() )
			Gunsmith.GunsmithLoadoutManager.ApplyBuild( WeaponResource, _weaponModel,
				Gunsmith.GunsmithLoadoutManager.BuildCode( WeaponResource, MuzzlePart ) );
	}

	private BoxCollider _movementBox;

	/// <summary>
	/// The box players have (the player prefab's "Collider"), so players bump into bots instead of walking through them.
	/// It's tagged "movement", which shots and sight checks skip: bullets still go by the hitboxes. Each machine makes its
	/// own, like the weapon model, since every player's movement runs on their own machine.
	/// </summary>
	private void AttachMovementBox()
	{
		if ( _dying || _movementBox.IsValid() )
			return;

		var box = new GameObject( GameObject, true, "Collider" );
		box.Flags |= GameObjectFlags.NotSaved | GameObjectFlags.NotNetworked;
		box.Tags.Add( "movement" );
		_movementBox = box.Components.Create<BoxCollider>();
		_movementBox.Center = new Vector3( 0f, 0f, 32f );
		_movementBox.Scale = new Vector3( 32f, 32f, 64f );
	}

	private Shootable _weaponShootable;

	/// <summary> The gun's Shootable, read from its prefab: damage, fire rate, shot sound and flash. </summary>
	private Shootable WeaponShootable
	{
		get
		{
			if ( !_weaponShootable.IsValid() && WeaponResource?.MainPrefab is { } prefab && prefab.IsValid() )
				_weaponShootable = prefab.GetComponentInChildren<Shootable>( true );
			return _weaponShootable;
		}
	}

	/// <summary>
	/// The guns bots are issued: every finished automatic primary (rifles, SMGs and LMGs). A bolt-action like the M700
	/// doesn't suit the bots' bursts, and WIP guns (the SCAR-H) wait until they're done.
	/// </summary>
	public static IEnumerable<EquipmentResource> WeaponPool() => ResourceLibrary.GetAll<EquipmentResource>()
		.Where( x => x.Slot == EquipmentSlot.Primary && !x.IsWip && CategoryShare( x.Category ) > 0f
			&& x.MainPrefab.IsValid() && x.WorldModelPrefab.IsValid()
			&& !Gunsmith.GunsmithLoadoutManager.IsMergedWeaponResource( x ) );

	/// <summary>
	/// How the guns are shared out: half riflemen, three in ten SMGs, and one in five machine gunners (a fire team's
	/// automatic rifleman). A category's share is split between its guns, so adding a gun doesn't change the mix.
	/// </summary>
	private static float CategoryShare( WeaponCategory category ) => category switch
	{
		WeaponCategory.AssaultRifle => 0.5f,
		WeaponCategory.SMG => 0.3f,
		WeaponCategory.LMG => 0.2f,
		_ => 0f
	};

	/// <summary>
	/// The share of soldiers issued a suppressor. More armies issue them every year: the US Marines have put one on every
	/// infantry rifle since 2020, and special forces have used them for much longer.
	/// </summary>
	private const float SuppressorShare = 0.25f;

	/// <summary>
	/// A suppressor for a new soldier's <paramref name="weapon"/>, for about one in four (<see cref="SuppressorShare"/>):
	/// one of the Muzzle-slot suppressors the gunsmith offers for that gun. Null for the rest, or if it takes none.
	/// </summary>
	public static Gunsmith.GunsmithPart RollMuzzle( EquipmentResource weapon )
	{
		if ( weapon is null || Game.Random.Float() >= SuppressorShare )
			return null;

		var suppressors = ResourceLibrary.GetAll<Gunsmith.GunsmithPart>()
			.Where( x => x.Category == Gunsmith.GunsmithPartType.Muzzle && x.IsSuppressor && x.MainPrefab.IsValid() && x.Supports( weapon ) )
			.ToList();
		return suppressors.Count > 0 ? Game.Random.FromList( suppressors ) : null;
	}

	/// <summary> A gun for a new soldier, or null (keep the prefab's) if none are loaded. </summary>
	public static EquipmentResource RollWeapon()
	{
		var pool = WeaponPool().ToList();
		if ( pool.Count == 0 )
			return null;

		var perCategory = pool.GroupBy( x => x.Category ).ToDictionary( x => x.Key, x => x.Count() );
		var weights = pool.Select( x => CategoryShare( x.Category ) / perCategory[x.Category] ).ToList();
		var roll = Game.Random.Float( 0f, weights.Sum() );
		for ( var i = 0; i < pool.Count; i++ )
		{
			roll -= weights[i];
			if ( roll <= 0f )
				return pool[i];
		}

		return pool[^1];
	}

	private void DropWeaponModel()
	{
		if ( !_weaponModel.IsValid() )
			return;

		var weapon = _weaponModel;
		_weaponModel = null;
		var position = weapon.WorldPosition;
		var rotation = weapon.WorldRotation;
		weapon.Destroy();

		if ( !Networking.IsHost || WeaponResource is null )
			return;

		var dropped = DroppedEquipment.Create( WeaponResource, position, rotation, networkSpawn: false );
		dropped.ApplySavedAttachments = false;
		var templateAmmo = WeaponResource.MainPrefab.IsValid()
			? WeaponResource.MainPrefab.GetComponentInChildren<WeaponAmmo>( true )
			: null;
		var magazineSize = Math.Max( 1, templateAmmo?.MaxAmmo ?? 30 );
		var ammo = dropped.GameObject.Components.Create<WeaponAmmo>();
		ammo.MaxAmmo = magazineSize;
		ammo.Ammo = magazineSize;
		ammo.ReserveAmmo = magazineSize * 2;
		dropped.GameObject.NetworkSpawn();
	}

	/// <summary> With no bone objects, the bone the gun is moved onto every frame, and its offset from that bone. </summary>
	private BoneCollection.Bone _handBone;
	private Transform _handOffset = global::Transform.Zero;

	private GameObject GetWeaponHold()
	{
		if ( _weaponHold.IsValid() )
			return _weaponHold;

		if ( !Renderer.IsValid() )
			return null;

		if ( !Renderer.CreateBoneObjects )
			return CreateHandFollower();

		var hold = MilitaryUniform.UsesHumanSkeleton( Renderer.Model ) ? null
			: Renderer.GetBoneObject( "hold_r" ) ?? Renderer.GetBoneObject( "hold_R" );

		if ( hold.IsValid() )
			return hold;

		var hand = Renderer.GetBoneObject( "r_hand" )
			?? Renderer.GetBoneObject( "hand_R" );

		if ( !hand.IsValid() )
			return null;

		_weaponHold = new GameObject( true, "WeaponHold" );
		_weaponHold.Parent = hand;
		_weaponHold.LocalTransform = MilitaryUniform.WeaponHandOffset( Renderer.Model );

		return _weaponHold;
	}

	/// <summary> Where the gun sits in a hand bone, for skeletons with no hold bone. The Theater puts replayed guns there too. </summary>
	internal static Transform HandHoldOffset => new( new Vector3( -5.199091f, 1.812593f, 4.880827f ),
		new Rotation( 0.006424597f, -0.9902432f, 0.04879934f, 0.130368f ) );

	/// <summary>
	/// A bot has no bone objects (see <see cref="BotSystem.FollowHands"/>), so its gun goes on an object of its own
	/// that <see cref="FollowHand"/> puts in the hand every frame.
	/// </summary>
	private GameObject CreateHandFollower()
	{
		var bones = Renderer.Model?.Bones;
		if ( bones is null )
			return null;

		_handBone = MilitaryUniform.UsesHumanSkeleton( Renderer.Model ) ? null
			: bones.GetBone( "hold_r" ) ?? bones.GetBone( "hold_R" );
		_handOffset = global::Transform.Zero;
		if ( _handBone is null )
		{
			_handBone = bones.GetBone( "r_hand" ) ?? bones.GetBone( "hand_R" );
			_handOffset = MilitaryUniform.WeaponHandOffset( Renderer.Model );
		}

		if ( _handBone is null )
			return null;

		_weaponHold = new GameObject( GameObject, true, "WeaponHold" );
		_weaponHold.Flags |= GameObjectFlags.NotSaved | GameObjectFlags.NotNetworked;
		FollowHand();
		return _weaponHold;
	}

	/// <summary> Put the gun in the hand as this frame's animation has it. </summary>
	internal void FollowHand()
	{
		if ( _handBone is null || !_weaponHold.IsValid() || !Renderer.IsValid() )
			return;

		if ( Renderer.TryGetBoneTransform( _handBone, out var hand ) )
		{
			if ( _handBone.Name is "hand_R" or "r_hand" )
				_handOffset = MilitaryUniform.WeaponHandOffset( Renderer.Model );
			_weaponHold.WorldTransform = hand.WithScale( 1f ).ToWorld( _handOffset );
		}
	}

	private readonly BotSupportHand _supportHand = new();
	private readonly BotSupportHand _gripHand = new( true );
	private float _supportGripWeight;

	/// <summary>Finish the gun and support arm together, using the pose the renderer will draw this frame.</summary>
	internal void FinishWeaponPose()
	{
		if ( _weaponModel.IsValid() ) _weaponModel.LocalTransform = global::Transform.Zero;
		FollowHand();
		var target = GetWeaponWorldModel()?.IkLeftHand;
		if ( !IsAlive || IsReloadClipPlaying || !Renderer.IsValid() || !target.IsValid() || !target.Active )
		{
			_supportGripWeight = 0f;
			return;
		}

		_supportGripWeight = MathF.Min( 1f, _supportGripWeight + Time.Delta / .2f );
		// Long handguards can fall beyond the support arm during a low carry or a turn. Bring the whole gun
		// and its gripping hand within both arms' reach before fitting the support arm; never stretch a wrist.
		var rightBone = Renderer.Model.Bones.GetBone( "hand_R" ) ?? Renderer.Model.Bones.GetBone( "r_hand" );
		if ( rightBone is not null && Renderer.SceneModel.IsValid() )
		{
			var right = Renderer.SceneModel.GetBoneWorldTransform( rightBone.Index );
			var shift = Vector3.Zero;
			for ( var i = 0; i < 4; i++ )
			{
				var leftAt = target.WorldPosition + shift;
				shift += _supportHand.Reachable( Renderer, leftAt ) - leftAt;
				var rightAt = right.Position + shift;
				shift += _gripHand.Reachable( Renderer, rightAt ) - rightAt;
			}
			shift *= _supportGripWeight;
			if ( shift.LengthSquared > .0001f )
			{
				_gripHand.Apply( Renderer, right.WithPosition( right.Position + shift ) );
				_weaponModel.WorldPosition += shift;
			}
		}
		var hand = Renderer.WorldTransform.ToLocal( target.WorldTransform );
		hand = MilitaryUniform.HandIkTransform( Renderer.Model, "hand_left", hand );
		_supportHand.Apply( Renderer, Renderer.WorldTransform.ToWorld( hand ), _supportGripWeight );
	}

	[Rpc.Broadcast]
	private void DoShootEffects( Vector3 startPosition, Vector3 endPosition, bool usesTracerRounds, bool hit )
	{
		var suppressed = IsSuppressed;
		MatchRecorder.NoteShot( GameObject, suppressed );
		EnsureReferences();
		AttachWeaponModel();

		var direction = (endPosition - startPosition).Normal;
		// The end of the suppressor, or of the barrel.
		var muzzle = GetWeaponWorldModel()?.DischargeMuzzle;
		var shootable = WeaponShootable;

		// A flash is seen on some shots, as a player's gun rolls it (Shootable.PlayDischargeEffects), and hardly ever
		// through a suppressor. Bots used to flash on every round.
		GameObject flashPrefab;
		float flashChance;
		if ( suppressed )
		{
			flashPrefab = shootable?.SuppressedMuzzleFlashPrefab;
			flashChance = shootable?.SuppressedMuzzleFlashChance ?? 0f;
		}
		else
		{
			flashPrefab = shootable?.MuzzleFlashPrefab;
			if ( !flashPrefab.IsValid() && !string.IsNullOrWhiteSpace( MuzzleFlashPrefab ) )
				flashPrefab = GameObject.GetPrefab( MuzzleFlashPrefab );
			flashChance = shootable?.MuzzleFlashChance ?? 1f;
		}

		// Nobody here would see the flash of a bot shooting behind them or a few pixels tall: don't make one.
		if ( flashPrefab.IsValid() && Game.Random.Float() < flashChance && BotSystem.ShouldShowEffect( startPosition ) )
		{
			var flash = muzzle.IsValid()
				? flashPrefab.Clone( new CloneConfig { Parent = muzzle, Transform = global::Transform.Zero, StartEnabled = true } )
				: flashPrefab.Clone( new CloneConfig { Transform = new Transform( startPosition, Rotation.LookAt( direction ) ), StartEnabled = true } );

			if ( flash.IsValid() )
				flash.Flags |= GameObjectFlags.NotSaved | GameObjectFlags.NotNetworked;
		}

		if ( usesTracerRounds && !string.IsNullOrWhiteSpace( TracerEffectPrefab ) && GameObject.GetPrefab( TracerEffectPrefab ).IsValid() )
		{
			var tracerObject = GameObject.Clone( TracerEffectPrefab, new CloneConfig
			{
				Transform = new Transform( startPosition, Rotation.LookAt( direction ) ),
				StartEnabled = true
			} );

			if ( tracerObject.IsValid() )
			{
				tracerObject.Flags |= GameObjectFlags.NotSaved | GameObjectFlags.NotNetworked;

				if ( tracerObject.GetComponentInChildren<Tracer>() is { } tracer )
					tracer.EndPoint = endPosition;
			}
		}

		// Shots from a fight further off than the sound carries would be silent here: don't start them. The rest fall off
		// with distance as a real blast does, muffled through walls (GunshotAudio).
		var shootSound = (suppressed ? shootable?.SuppressedShootSound : null) ?? shootable?.ShootSound
			?? (string.IsNullOrWhiteSpace( ShootSound ) ? null : ResourceLibrary.Get<SoundEvent>( ShootSound ));
		if ( shootSound is not null && BotSystem.CanHear( shootSound, startPosition ) )
			GunshotAudio.Play( shootSound, startPosition, direction, false );

		// The round's crack for anyone it passes, and what it strikes, heard when it gets there. A miss flies on to the
		// gun's range.
		if ( shootable.IsValid() )
		{
			var flightEnd = hit ? endPosition : startPosition + direction * shootable.MaxRange;
			BulletFlyby.Pass( shootable, startPosition, flightEnd, flyby: true, impact: hit, reflections: true );
		}

		Renderer?.Set( "b_attack", true );
	}

	private Vector3 GetMuzzlePosition()
	{
		var muzzle = GetWeaponWorldModel()?.DischargeMuzzle;
		if ( muzzle.IsValid() )
			return muzzle.WorldPosition;

		return EyePosition + WorldRotation.Forward * 32f;
	}

	private WorldModel _worldModel;

	private WorldModel GetWeaponWorldModel()
	{
		if ( !_weaponModel.IsValid() )
			return null;

		if ( !_worldModel.IsValid() || _worldModel.GameObject.Root != _weaponModel.Root )
			_worldModel = _weaponModel.GetComponentInChildren<WorldModel>();
		return _worldModel;
	}

	private void UpdateAnimation()
	{
		if ( !Renderer.IsValid() )
			return;

		if ( !IsAlive )
			return;

		var velocity = UpdateMoveVelocity();
		var forward = WorldRotation.Forward.Dot( velocity );
		var sideward = WorldRotation.Right.Dot( velocity );

		// Past the blend's ring of clips no clip steps far enough: hold the ring's clips and play the legs faster. A runner
		// goes faster mostly by taking longer strides, which the clips can't, and legs sped up the whole way (a strafe's jog
		// at 1.36x, the hunting sprint at 1.29x: 220-260 steps a minute) looked like running faster than the bot moved. So
		// the legs speed up by the square root of what's missing, and the feet slide the rest (~14% on a strafe).
		var speed = MathF.Sqrt( forward * forward + sideward * sideward );
		var rate = 1f;
		// The human body's graph (citizen_human) has walk, run and sprint clips and picks between them by speed, as for a
		// player, so it takes the true velocity. The ring is rigged_human's: clamped to it, a sprinting bot's legs jogged.
		var humanGraph = MilitaryUniform.UsesHumanSkeleton( Renderer.Model );
		if ( speed > 1f && !humanGraph )
		{
			var reach = RingReach( IsCrouching ? CrouchedClipRing : StoodClipRing, new Vector2( sideward / speed, forward / speed ) );
			if ( speed > reach )
			{
				rate = MathF.Min( MathF.Sqrt( speed / reach ), MaxMoveRate );
				forward *= reach / speed;
				sideward *= reach / speed;
			}
		}

		Renderer.Set( "holdtype", (int)AnimationHelper.HoldTypes.Rifle );
		Renderer.Set( "holdtype_handedness", (int)AnimationHelper.Hand.Right );
		Renderer.Set( "b_twohanded", true );
		Renderer.Set( "b_grounded", true );
		Renderer.Set( "move_speed", velocity.Length );
		Renderer.Set( "move_groundspeed", velocity.WithZ( 0f ).Length );
		Renderer.Set( "move_x", forward );
		Renderer.Set( "move_y", sideward );
		Renderer.Set( "move_z", velocity.z );
		Renderer.Set( "move_rate", rate );
		Renderer.Set( "speed_move", 1f );
		if ( humanGraph )
		{
			// As a player's body is driven (PlayerPawn.Movement, AnimationHelper): the run style, which sprints at a sprint,
			// and where the bot is going. It has no input, so what it wants is what it does.
			var direction = MathF.Atan2( sideward, forward ).RadianToDegree().NormalizeDegrees();
			Renderer.Set( "move_direction", direction );
			Renderer.Set( "move_style", (int)AnimationHelper.MoveStyles.Run );
			Renderer.Set( "wish_direction", direction );
			Renderer.Set( "wish_speed", velocity.Length );
			Renderer.Set( "wish_groundspeed", velocity.WithZ( 0f ).Length );
			Renderer.Set( "wish_x", forward );
			Renderer.Set( "wish_y", sideward );
			Renderer.Set( "wish_z", velocity.z );
		}

		Renderer.Set( "duck", IsCrouching ? 1f : 0f );

		// The host decides where the bot aims and syncs it, so every client sees it look at what it's shooting.
		var aim = AimDirection.IsNearZeroLength ? WorldRotation.Forward : AimDirection;
		// In a fight the gun comes up to the shoulder, the chest squares up behind it and the head drops onto the stock,
		// eyes still on the target. Not at a run: a runner carries it.
		var shouldered = IsAimingIn && !IsReloadClipPlaying && speed < MaxShoulderedSpeed;
		_aimBodyWeight = MathX.Lerp( _aimBodyWeight, shouldered ? 1f : 0.75f, Time.Delta * 8f );
		_headDrop = MathX.Lerp( _headDrop, shouldered ? ShoulderedHeadDrop : 0f, Time.Delta * 8f );
		Renderer.SetLookDirection( "aim_eyes", aim, 1f );
		Renderer.SetLookDirection( "aim_head", Lowered( aim, _headDrop ), 1f );
		Renderer.SetLookDirection( "aim_body", aim, _aimBodyWeight );

		UpdateLeftHandIk();
		UpdateRightHandIk( aim, shouldered );
	}

	/// <summary>
	/// The outer ring of rigged_human.vanmgrph's lower-body blend, as velocities (right, forward) in u/s, clockwise from
	/// ahead: sprint, then the jogs. Each clip sits at the velocity its planted feet carry the body, so inside the ring
	/// the feet keep pace with the ground (the walks are an inner ring at ~33). The clips used to sit 1.4-2.5x faster
	/// than they step, so a bot strafing at 126 u/s stepped like one at ~70 and glided. Keep in step with the graph.
	/// </summary>
	private static readonly Vector2[] StoodClipRing =
	{
		new( 0f, 178f ), new( 81f, 90f ), new( 93f, 0f ), new( 62f, -71f ),
		new( 0f, -91f ), new( -67f, -62f ), new( -93f, 0f ), new( -65f, 86f ),
	};

	/// <summary> The crouched blend's clips, as <see cref="StoodClipRing"/>. </summary>
	private static readonly Vector2[] CrouchedClipRing =
	{
		new( 0f, 38f ), new( 26f, 27f ), new( 32f, 0f ), new( 26f, -29f ),
		new( 0f, -39f ), new( -26f, -29f ), new( -32f, 0f ), new( -26f, 29f ),
	};

	/// <summary> The fastest the legs play (the graph's move_rate), however fast the bot is moved: any faster is no runner's cadence. </summary>
	private const float MaxMoveRate = 1.25f;

	private Vector3 _lastAnimPosition;
	private Vector3 _moveVelocity;
	private bool _hasAnimPosition;

	/// <summary>
	/// How the bot is moving, from how far it went since last frame. The agent's velocity is only known to the host (on
	/// clients, where the position comes over the network, it's zero, so they saw bots glide on idle legs), and it leaves
	/// out the agent's shoves round other bots.
	/// </summary>
	private Vector3 UpdateMoveVelocity()
	{
		var position = WorldPosition;
		if ( !_hasAnimPosition || Time.Delta <= 0f )
		{
			_hasAnimPosition = true;
			_lastAnimPosition = position;
			return _moveVelocity;
		}

		var moved = (position - _lastAnimPosition) / Time.Delta;
		_lastAnimPosition = position;

		// Faster than anyone runs: a teleport, not a step.
		if ( moved.WithZ( 0f ).Length > 1000f )
			return _moveVelocity;

		_moveVelocity = _moveVelocity.LerpTo( moved, Time.Delta * 12f );
		return _moveVelocity;
	}

	/// <summary> How far out <paramref name="ring"/> reaches along <paramref name="direction"/> (a unit vector, right/forward). </summary>
	private static float RingReach( Vector2[] ring, Vector2 direction )
	{
		for ( var i = 0; i < ring.Length; i++ )
		{
			var corner = ring[i];
			var edge = ring[(i + 1) % ring.Length] - corner;
			var cross = direction.x * edge.y - direction.y * edge.x;
			if ( MathF.Abs( cross ) < 0.0001f )
				continue;

			var distance = (corner.x * edge.y - corner.y * edge.x) / cross;
			var along = (corner.x * direction.y - corner.y * direction.x) / cross;
			if ( distance > 0f && along >= 0f && along <= 1f )
				return distance;
		}

		return ring[0].Length;
	}

	/// <summary>
	/// The left hand on the gun's handguard (its world model's IkLeftHand), as a player's <see cref="AnimationHelper"/>
	/// puts it. The rifle pose alone doesn't know where a gun's handguard is, so on a short gun like the Kastov-74u the
	/// hand missed it. This gives the animation graph a starting pose; <see cref="FinishWeaponPose"/> corrects the arm
	/// after the right hand and gun have moved for this frame. Off while the reload clip plays, which takes the hand to
	/// the magazine, and only then: a bot's reload runs 1.7-8 s (the gun's reload time, slower for green bots), and for
	/// the rest of it the hand hung off the gun where the rifle pose has it.
	/// </summary>
	private void UpdateLeftHandIk()
	{
		var target = GetWeaponWorldModel()?.IkLeftHand;
		if ( IsReloadClipPlaying || !target.IsValid() || !target.Active )
		{
			Renderer.Set( "ik.hand_left.enabled", false );
			return;
		}

		var hand = Renderer.WorldTransform.ToLocal( target.WorldTransform );
		hand = MilitaryUniform.HandIkTransform( Renderer.Model, "hand_left", hand );
		Renderer.Set( "ik.hand_left.enabled", true );
		Renderer.Set( "ik.hand_left.position", hand.Position );
		Renderer.Set( "ik.hand_left.rotation", hand.Rotation );
	}

	/// <summary> How long (s) the rifle reload clip (SMG_2H_Reload_01) has the hands. </summary>
	private const float ReloadClipSeconds = 1.67f;
	/// <summary>
	/// Faster than this (u/s) the bot is sprinting (<see cref="IsSprinting"/>) and carries its gun. Its walk, a player's
	/// with the same gun, is under it.
	/// </summary>
	private const float MaxShoulderedSpeed = 190f;
	/// <summary>
	/// How far in front of the butt a shooter's eye sits along the gun, the cheek on the stock. With the head dropped
	/// (<see cref="ShoulderedHeadDrop"/>) this puts the butt at the shoulder: any longer and it pokes out behind the
	/// head, any shorter and a Kastov's or an RPK's handguard is out of the left hand's reach (hc1_bot_grip_preview).
	/// </summary>
	public const float ButtToEye = 8f;
	/// <summary> How far (degrees) the head tips forward onto the stock while shouldered. </summary>
	public const float ShoulderedHeadDrop = 20f;

	/// <summary> Since the reload clip started, on every machine (<see cref="PlayReloadAnimation"/>). </summary>
	private TimeSince _sinceReloadClip = 999f;
	private float _aimBodyWeight = 0.75f;
	private float _headDrop;
	private WorldModel _sightedGun;
	private Vector3 _eyeOnGun;

	private bool IsReloadClipPlaying => _sinceReloadClip < ReloadClipSeconds;

	/// <summary> <paramref name="aim"/> tipped <paramref name="degrees"/> further down. </summary>
	public static Vector3 Lowered( Vector3 aim, float degrees )
	{
		var flat = aim.WithZ( 0f );
		if ( degrees == 0f || flat.IsNearZeroLength )
			return aim;

		var pitch = MathF.Max( MathF.Atan2( aim.z, flat.Length ) - degrees.DegreeToRadian(), -1.5f );
		return flat.Normal * MathF.Cos( pitch ) + Vector3.Up * MathF.Sin( pitch );
	}

	/// <summary>
	/// In a fight (<see cref="IsAimingIn"/>) the right hand brings the gun up to the shoulder, sighted along the aim
	/// (<see cref="ShoulderedHandIk"/>), and the left hand follows it. The rifle pose on its own only carries a gun at
	/// the hip (and lowers it after a second stood still), so a bot shooting at you never looked like it was aiming.
	/// The graph blends the IK in and out over 0.35 s: the gun comes up and goes down.
	/// </summary>
	private void UpdateRightHandIk( Vector3 aim, bool shouldered )
	{
		var gun = shouldered ? GetWeaponWorldModel() : null;
		if ( gun.IsValid() && gun != _sightedGun )
		{
			_sightedGun = gun;
			_eyeOnGun = EyeOnGun( gun );
		}

		if ( !gun.IsValid() || ShoulderedHandIk( Renderer, gun, _eyeOnGun, aim ) is not { } hand )
		{
			Renderer.Set( "ik.hand_right.enabled", false );
			return;
		}

		Renderer.Set( "ik.hand_right.enabled", true );
		Renderer.Set( "ik.hand_right.position", hand.Position );
		Renderer.Set( "ik.hand_right.rotation", hand.Rotation );
	}

	/// <summary>
	/// Where a shooter's eye sits on <paramref name="gun"/>, in its space: on the line of its sights, taken as half a unit
	/// under the top of the gun (irons, a carry handle and a built-in scope alike), <paramref name="buttToEye"/> in front
	/// of its butt. From the model's bounds, since the models put sights and stocks in very different places: a FAMAS's
	/// carry handle is five units over its bore, a Kastov's irons two.
	/// </summary>
	public static Vector3 EyeOnGun( WorldModel gun, float buttToEye = ButtToEye )
	{
		var renderer = gun.ModelRenderer.IsValid() ? gun.ModelRenderer : gun.GetComponentInChildren<SkinnedModelRenderer>();
		if ( renderer?.Model is not { } model )
			return new Vector3( -8f, 0f, 6f );

		var bounds = model.Bounds.Transform( gun.WorldTransform.ToLocal( renderer.WorldTransform ) );
		var sights = bounds.Maxs.z - 0.5f;
		if ( gun.Muzzle.IsValid() )
		{
			var bore = gun.WorldTransform.PointToLocal( gun.Muzzle.WorldPosition ).z;
			sights = sights.Clamp( bore + 1.5f, bore + 5f );
		}

		return new Vector3( bounds.Mins.x + buttToEye, 0f, sights );
	}

	/// <summary>
	/// The right hand's IK target (in <paramref name="body"/>'s space) that holds <paramref name="gun"/> level at the
	/// shoulder, aimed along <paramref name="aim"/>, with <paramref name="eyeOnGun"/> (<see cref="EyeOnGun"/>) at the
	/// right eye. The gun rides the hand rigidly (a hold bone, or the hand and an offset), so the hand keeps its grip.
	/// Null when the body has no eye or hand to go by.
	/// </summary>
	public static Transform? ShoulderedHandIk( SkinnedModelRenderer body, WorldModel gun, Vector3 eyeOnGun, Vector3 aim )
	{
		if ( aim.IsNearZeroLength || (body.GetAttachment( "eye_R_forward" ) ?? body.GetAttachment( "eyes" )) is not { } eye )
			return null;

		var handBone = body.Model?.Bones.GetBone( "hand_R" ) ?? body.Model?.Bones.GetBone( "r_hand" );
		if ( handBone is null )
			return null;

		// The gun still has last frame's transform here, while the bot may already have moved or turned.
		// Measuring the mount from those two poses feeds that movement back into the next IK target.
		var holdBone = MilitaryUniform.UsesHumanSkeleton( body.Model ) ? null
			: body.Model.Bones.GetBone( "hold_r" ) ?? body.Model.Bones.GetBone( "hold_R" );
		var grip = holdBone is null ? MilitaryUniform.WeaponHandOffset( body.Model )
			: handBone.LocalTransform.ToLocal( holdBone.LocalTransform );
		var rotation = Rotation.LookAt( aim.Normal, Vector3.Up );
		var sighted = new Transform( eye.Position - rotation * eyeOnGun, rotation );
		return body.WorldTransform.ToLocal( sighted.ToWorld( grip.ToLocal( global::Transform.Zero ) ) );
	}

	private bool IsEnemyAlive( Component target )
	{
		if ( !target.IsValid() )
			return false;

		if ( !GameUtils.IsFreeForAllMode && GameUtils.GetTeamFromComponent( target ) == Team )
			return false;

		return target switch
		{
			PlayerPawn player => player.HealthComponent.IsValid() && player.HealthComponent.State == LifeState.Alive
				&& !player.HealthComponent.IsGodMode,
			LightweightCombatBot bot => bot.IsAlive,
			_ => false
		};
	}

	private static bool HitTarget( GameObject hit, Component target )
	{
		if ( !hit.IsValid() || !target.IsValid() )
			return false;

		return hit == target.GameObject || hit.Root == target.GameObject.Root || hit.IsDescendant( target.GameObject );
	}

	void IRespawnable.OnKill( DamageInfo damageInfo )
	{
		if ( _dying )
			return;

		_dying = true;
		GameObject.Tags.Remove( "player" );
		GameObject.Tags.Add( "dead" );
		// Players walk through bodies (their movement ignores "ragdoll", like player bodies), and footsteps look
		// through them to the floor (PlayerFootsteps).
		GameObject.Tags.Add( "ragdoll" );
		GameObject.Tags.Add( "corpse" );
		if ( _movementBox.IsValid() )
			_movementBox.GameObject.Destroy();

		Agent?.Stop();
		if ( Agent.IsValid() )
		{
			Agent.Enabled = false;
		}

		DropWeaponModel();

		if ( Renderer.IsValid() )
		{
			Renderer.UseAnimGraph = false;
			var physics = Renderer.Components.GetOrCreate<Sandbox.ModelPhysics>();
			physics.Enabled = true;

			// Most go down over a second or two as their muscles let go; only some drop on the spot (DeathPlan).
			DyingBody.Begin( physics, DeathPlan.Choose( damageInfo, GameObject.Id, WorldPosition, WorldRotation,
				_moveVelocity, IsCrouching, down: false ) );
		}

		GameObject.DestroyAsync( CorpseLifetime );
	}

	void IGameEventHandler<KillEvent>.OnGameEvent( KillEvent eventArgs )
	{
		if ( !Networking.IsHost )
			return;

		var damageInfo = eventArgs.DamageInfo;
		var killerBot = GameUtils.GetLightweightBotFromComponent( damageInfo.Attacker );
		var victimBot = GameUtils.GetLightweightBotFromComponent( damageInfo.Victim );

		var killerIsThis = killerBot == this;
		var victimIsThis = victimBot == this;
		if ( !killerIsThis && !victimIsThis )
			return;

		var killerTeam = GameUtils.GetTeamFromComponent( damageInfo.Attacker );
		var victimTeam = GameUtils.GetTeamFromComponent( damageInfo.Victim );
		var isFriendly = killerTeam != Team.Unassigned && killerTeam == victimTeam;
		var isSuicide = killerIsThis && victimIsThis;

		if ( killerIsThis )
		{
			if ( isFriendly && !isSuicide )
			{
				Kills--;
				Score += TeamKillScore;
			}
			else if ( isSuicide )
			{
				Kills--;
				Score += SuicideScore;
			}
			else
			{
				Kills++;
				Score += KillScore;
			}
		}

		if ( victimIsThis && !isFriendly )
		{
			Deaths++;
		}

		LightweightBotManager.Instance?.RecordStats( this );
	}

	/// <summary> Carry the bot's score over from its last life, see <see cref="LightweightBotManager"/>. Host only. </summary>
	internal void RestoreStats( int kills, int deaths, int score )
	{
		Kills = kills;
		Deaths = deaths;
		Score = score;
	}

	void IGameEventHandler<ResetScoresEvent>.OnGameEvent( ResetScoresEvent eventArgs )
	{
		if ( !Networking.IsHost )
			return;

		Kills = 0;
		Deaths = 0;
		Score = 0;
	}

	void IGameEventHandler<DamageTakenEvent>.OnGameEvent( DamageTakenEvent eventArgs )
	{
		var damageInfo = eventArgs.DamageInfo;

		// A burn isn't a hit: no blood, and nothing to tell the bot who started the fire.
		var burn = damageInfo.Flags.HasFlag( DamageFlags.Burn );
		if ( damageInfo.Damage > 0f && !burn && BloodEffect.IsValid() && !damageInfo.Flags.HasFlag( DamageFlags.Zone )
			&& BotSystem.ShouldShowEffect( WorldPosition + Vector3.Up * 44f ) )
		{
			// Splash damage can report the blast origin, well outside the victim.
			var chest = WorldPosition + Vector3.Up * 44f;
			var impact = damageInfo.Position;
			if ( impact.DistanceSquared( chest ) > 32f * 32f )
				impact = chest;
			var effectRotation = damageInfo.Force.IsNearZeroLength
				? WorldRotation
				: Rotation.LookAt( damageInfo.Force.Normal, Vector3.Up );
			var blood = BloodEffect.Clone( new CloneConfig()
			{
				StartEnabled = true,
				Transform = new( impact, effectRotation ),
				Name = $"Blood effect from ({GameObject})"
			} );

			if ( blood.IsValid() && !blood.Components.Get<DestroyAfter>().IsValid() )
				blood.DestroyAsync( 2f );
		}

		if ( !Networking.IsHost )
			return;

		var attacker = damageInfo.Attacker;
		if ( !burn && attacker.IsValid() && IsEnemyAlive( attacker ) )
			OnShotBy( attacker );
	}

	void IAreaDamageReceiver.ApplyAreaDamage( AreaDamage component )
	{
		if ( !HealthComponent.IsValid() )
			return;

		var damageInfo = new DamageInfo( component.Attacker, component.Damage, component.Inflictor, component.WorldPosition,
			Flags: component.DamageFlags );
		HealthComponent.TakeDamage( damageInfo );
	}
}

public sealed partial class LightweightBotManager : SingletonComponent<LightweightBotManager>,
	IGameEventHandler<ResetScoresEvent>
{
	public const string BotTag = "hc1_lightweight_bot";

	private static readonly string[] BotNames =
	{
		"Raven", "Ghost", "Blaze", "Viper", "Reaper", "Mako", "Falcon", "Nova", "Atlas", "Echo",
		"Hawk", "Cobra", "Wolf", "Talon", "Rook", "Jackal", "Onyx", "Specter", "Bishop", "Sable",
		"Hound", "Drake", "Kodiak", "Vulture", "Nomad", "Havoc", "Fury", "Colt", "Spark", "Striker"
	};

	[Property] public string BotPrefabPath { get; set; } = "prefabs/bots/hc1_combat_bot.prefab";
	[Property] public float MinSpawnDistanceFromPlayers { get; set; } = 900f;

	/// <summary>
	/// Chance a bot spawns at one of the map's own player starts instead of the team spawns. Only starts a bot can walk
	/// away from count (<see cref="IsOnMainNavMesh"/>): Flatgrass's are all on its building's roof, so it has none.
	/// </summary>
	[Property, Range( 0, 1 )] public float MapSpawnChance { get; set; } = 0.35f;

	/// <summary>
	/// Map spawns closer than this to a living player are skipped, so bots don't appear in someone's face.
	/// </summary>
	[Property] public float MapSpawnMinPlayerDistance { get; set; } = 500f;
	[Property] public float MinSpawnDistanceFromBots { get; set; } = 800f;

	/// <summary>
	/// A bot doesn't spawn closer than this to a living teammate bot (~10 m), and a spot closer than twice this counts
	/// against it. At 150 units a team's reinforcements came in as a bunch and stayed one.
	/// </summary>
	[Property] public float MinSpawnDistanceFromTeammates { get; set; } = 400f;

	/// <summary>
	/// Bots spawn within this distance of a real player, so the fight comes to them instead of happening somewhere
	/// across a big map like Flatgrass.
	/// </summary>
	[Property] public float MaxSpawnDistanceFromPlayers { get; set; } = 3000f;

	/// <summary> How far from the real players enemy bots like to spawn; their teammates spawn at half this. </summary>
	[Property] public float PreferredSpawnDistance { get; set; } = 2000f;

	/// <summary> Scoreboard "Add bot" won't take a team past this many. </summary>
	public const int MaxTeamBots = 12;

	/// <summary>
	/// A bot on the scoreboard. Each life is a new <see cref="LightweightCombatBot"/>, so its name, team, personality
	/// and score are kept here and handed to the next one: a name is the same soldier all match, like a player.
	/// </summary>
	private sealed class BotIdentity
	{
		public string Name;
		public Team Team;
		public float Skill;
		/// <summary> How the soldier fights (its style and aggression come with it), rolled with its gun. </summary>
		public BotHabits? Habits;
		/// <summary> The soldier's issued gun, the same every life. </summary>
		public EquipmentResource Weapon;
		/// <summary> Its suppressor, if it was issued one with the gun. </summary>
		public Gunsmith.GunsmithPart Muzzle;
		public int Kills;
		public int Deaths;
		public int Score;
	}

	private int _nextBotIndex;
	private readonly List<BotIdentity> _roster = new();

	/// <summary> Bots added (positive) or kicked (negative) per team from the scoreboard, on top of the fill target. </summary>
	private readonly Dictionary<Team, int> _teamBotAdjustment = new();

	public IEnumerable<LightweightCombatBot> Bots => Scene.GetAllComponents<LightweightCombatBot>()
		.Where( x => x.IsValid() && x.GameObject.Tags.Has( BotTag ) );

	/// <summary> Can the local player add and kick bots? The host can, in modes that fill with bots. </summary>
	public static bool CanManageBots => (!Networking.IsActive || Networking.IsHost)
		&& GameMode.Instance.IsValid() && GameMode.Instance.Get<BotFillRule>() is { Active: true, UseLightweightNpcBots: true };

	/// <summary> Scoreboard "Add bot": one more bot on <paramref name="team"/> for the rest of the match. Host only. </summary>
	public void AddBot( Team team )
	{
		if ( Bots.Count( x => x.IsAlive && x.Team == team ) >= MaxTeamBots )
			return;

		_teamBotAdjustment[team] = GetAdjustment( team ) + 1;
		SpawnBot( team );
	}

	/// <summary> Scoreboard "Kick": take the bot called <paramref name="name"/> out of the match, one fewer on its team. Host only. </summary>
	public void KickBot( string name )
	{
		var identity = _roster.FirstOrDefault( x => x.Name == name );
		var team = identity?.Team ?? Bots.FirstOrDefault( x => x.BotName == name )?.Team ?? Team.Unassigned;
		_teamBotAdjustment[team] = GetAdjustment( team ) - 1;
		_roster.Remove( identity );

		foreach ( var bot in Bots.Where( x => x.BotName == name ).ToArray() )
			bot.GameObject.Destroy();
	}

	private int GetAdjustment( Team team ) => _teamBotAdjustment.TryGetValue( team, out var adjustment ) ? adjustment : 0;

	/// <summary> Keep a bot's score for its next life. Host only. </summary>
	public void RecordStats( LightweightCombatBot bot )
	{
		var identity = _roster.FirstOrDefault( x => x.Name == bot.BotName );
		if ( identity is null )
			return;

		identity.Kills = bot.Kills;
		identity.Deaths = bot.Deaths;
		identity.Score = bot.Score;
	}

	void IGameEventHandler<ResetScoresEvent>.OnGameEvent( ResetScoresEvent eventArgs ) => ResetRosterScores();

	private void ResetRosterScores()
	{
		foreach ( var identity in _roster )
		{
			identity.Kills = 0;
			identity.Deaths = 0;
			identity.Score = 0;
		}
	}

	public void Maintain( int targetPlayerCount, int maxTeamSize )
	{
		if ( IsProxy )
			return;

		if ( Networking.IsActive && !Networking.IsHost )
			return;

		RemoveLegacyClientBots();

		if ( GameUtils.IsFreeForAllMode )
		{
			MaintainFreeForAll( Math.Max( 0, targetPlayerCount + GetAdjustment( Team.Unassigned ) ) );
			return;
		}

		var targetPerTeam = Math.Max( 1, Math.Min( maxTeamSize, targetPlayerCount / 2 ) );
		MaintainTeam( Team.Terrorist, Math.Max( 0, targetPerTeam + GetAdjustment( Team.Terrorist ) ) );
		MaintainTeam( Team.CounterTerrorist, Math.Max( 0, targetPerTeam + GetAdjustment( Team.CounterTerrorist ) ) );
	}

	private void MaintainFreeForAll( int targetPlayerCount )
	{
		var realPlayers = GameUtils.AllPlayers.Count( x => x.IsConnected && !x.IsBot );
		var bots = Bots.Where( x => x.IsAlive ).ToList();

		while ( realPlayers + bots.Count > targetPlayerCount && bots.Count > 0 )
		{
			var bot = bots[^1];
			bots.RemoveAt( bots.Count - 1 );
			bot.GameObject.Destroy();
		}

		while ( realPlayers + bots.Count < targetPlayerCount )
		{
			var bot = SpawnBot( Team.Unassigned );
			if ( !bot.IsValid() )
				break;

			bots.Add( bot );
		}
	}

	private void MaintainTeam( Team team, int targetTeamSize )
	{
		var realPlayers = GameUtils.GetPlayers( team ).Count( x => x.IsConnected && !x.IsBot );
		var bots = Bots.Where( x => x.IsAlive && x.Team == team ).ToList();

		while ( realPlayers + bots.Count > targetTeamSize && bots.Count > 0 )
		{
			var bot = bots[^1];
			bots.RemoveAt( bots.Count - 1 );
			bot.GameObject.Destroy();
		}

		while ( realPlayers + bots.Count < targetTeamSize )
		{
			var bot = SpawnBot( team );
			if ( !bot.IsValid() )
				break;

			bots.Add( bot );
		}
	}

	/// <summary> A new bot on <paramref name="team"/>, at <paramref name="at"/> or else wherever suits it. Host only. </summary>
	public LightweightCombatBot SpawnBot( Team team, Transform? at = null )
	{
		if ( !GameObject.GetPrefab( BotPrefabPath ).IsValid() )
		{
			Log.Warning( $"Missing lightweight bot prefab: {BotPrefabPath}" );
			return null;
		}

		var index = _nextBotIndex++;
		var botObject = GameObject.Clone( BotPrefabPath, new CloneConfig
		{
			Name = $"Combat Bot {index + 1}",
			StartEnabled = false,
			Transform = at ?? GetSpawnTransform( team )
		} );

		if ( !botObject.IsValid() )
			return null;

		botObject.Flags |= GameObjectFlags.NotSaved;
		botObject.Tags.Add( BotTag );
		botObject.Tags.Add( "removable" );

		var bot = botObject.Components.Get<LightweightCombatBot>( true );
		if ( bot.IsValid() )
		{
			// A bot that died comes back as itself; otherwise a new soldier joins.
			var (namesInScene, namesInPlay) = BotNamesInScene();
			var identity = _roster.FirstOrDefault( x => x.Team == team && !namesInPlay.Contains( x.Name ) ) ?? CreateIdentity( team, namesInScene );
			bot.Team = team;
			bot.BotName = identity.Name;
			bot.Skill = identity.Skill;
			// Issued on the soldier's first life, and set before networking so clients spawn it with the same gun.
			if ( identity.Weapon is null )
			{
				identity.Weapon = LightweightCombatBot.RollWeapon();
				identity.Muzzle = LightweightCombatBot.RollMuzzle( identity.Weapon );
			}
			if ( identity.Weapon is not null )
			{
				bot.WeaponResource = identity.Weapon;
				bot.MuzzlePart = identity.Muzzle;
			}
			// How it fights goes with the gun it carries, and stays the same every life.
			identity.Habits ??= BotHabits.Roll( bot.WeaponResource?.Category );
			bot.Habits = identity.Habits.Value;
			bot.Aggression = identity.Habits.Value.Aggression;
			bot.RandomizePersonality = false;
			bot.RestoreStats( identity.Kills, identity.Deaths, identity.Score );
			// Select the body before networking and creating its weapon attachment bones.
			bot.ApplyTeamModel();
			// A GameObject per bone, moved every frame, is a lot for a hundred bots: without them the gun follows the
			// hand bone instead (BotSystem.FollowHands). Set before networking so every client's copy has none either.
			if ( BotSystem.LodEnabled && bot.Renderer.IsValid() )
				bot.Renderer.CreateBoneObjects = false;
		}

		if ( Networking.IsActive )
		{
			botObject.NetworkSpawn( true, null );
		}
		else
		{
			botObject.Enabled = true;
		}

		return bot;
	}

	/// <summary> The names of every bot in the scene, and of those in play: bodies are tagged "dead" and aren't. </summary>
	private (HashSet<string> All, HashSet<string> InPlay) BotNamesInScene()
	{
		var all = new HashSet<string>();
		var inPlay = new HashSet<string>();
		foreach ( var bot in Bots )
		{
			all.Add( bot.BotName );
			if ( !bot.GameObject.Tags.Has( "dead" ) )
				inPlay.Add( bot.BotName );
		}

		return (all, inPlay);
	}

	private BotIdentity CreateIdentity( Team team, HashSet<string> namesInScene )
	{
		var taken = new HashSet<string>( namesInScene );
		foreach ( var other in _roster )
			taken.Add( other.Name );

		var name = BotNames.FirstOrDefault( x => !taken.Contains( x ) );
		for ( var n = 2; name is null; n++ )
			name = BotNames.Select( x => $"{x} {n}" ).FirstOrDefault( x => !taken.Contains( x ) );

		var identity = new BotIdentity
		{
			Name = name,
			Team = team,
			Skill = LightweightCombatBot.RollSkill()
		};
		_roster.Add( identity );
		return identity;
	}

	public void ClearBots()
	{
		foreach ( var bot in Bots.ToArray() )
		{
			bot.GameObject.Destroy();
		}
	}

	private void RemoveLegacyClientBots()
	{
		foreach ( var clientBot in GameUtils.AllPlayers.Where( x => x.IsValid() && x.IsBot ).ToArray() )
		{
			clientBot.Kick( "Using lightweight NPC bots" );
		}
	}

	private Transform GetSpawnTransform( Team team )
	{
		if ( MapSpawnSettings.MapSpawnPointsAllowed && Random.Shared.Float() < MapSpawnChance && TryGetMapSpawn( out var mapSpawn ) )
			return mapSpawn;
		if ( MapSpawnSettings.NavMeshSpawnsAllowed && TryGetNavSpawn( team, out var navSpawn ) )
			return navSpawn;

		var spawnPoints = (team == Team.Unassigned ? GameUtils.GetSpawnPoints() : GameUtils.GetSpawnPoints( team )).ToArray();
		if ( spawnPoints.Length == 0 )
			return global::Transform.Zero;

		var candidates = spawnPoints
			.OrderByDescending( x => GetSpawnScore( x.Position ) )
			.Where( x => IsOnMainNavMesh( x.Position ) )
			.Take( 5 )
			.ToArray();

		var spawn = Random.Shared.FromArray( candidates, spawnPoints[0] );
		return spawn.Transform.WithScale( 1f );
	}

	/// <summary>
	/// Somewhere on the navmesh near the real players, so the fight comes to them: enemy bots around
	/// <see cref="PreferredSpawnDistance"/> away and out of their sight where there's cover, teammates closer in and
	/// away from the enemy. With no player in the world yet, the team spawns are used instead.
	/// </summary>
	private bool TryGetNavSpawn( Team team, out Transform transform )
	{
		transform = global::Transform.Zero;
		var players = GameUtils.PlayerPawns.Where( x => x.Team != Team.Unassigned || GameUtils.IsFreeForAllMode ).ToArray();
		if ( players.Length == 0 )
			return false;

		var enemies = players.Where( x => IsEnemy( team, x.Team ) ).ToArray();
		var anchors = enemies.Length > 0 ? enemies : players;
		var wantedDistance = enemies.Length > 0 ? PreferredSpawnDistance : PreferredSpawnDistance * 0.5f;
		var bots = Bots.Where( x => x.IsAlive ).ToArray();

		var candidates = new List<(Vector3 Position, float Score)>();
		for ( var i = 0; i < 24; i++ )
		{
			var anchor = Random.Shared.FromArray( anchors );
			if ( Scene.NavMesh.GetRandomPoint( anchor.WorldPosition, MaxSpawnDistanceFromPlayers ) is not { } point )
				continue;

			var enemyDistance = enemies.Select( x => x.WorldPosition.Distance( point ) ).DefaultIfEmpty( float.MaxValue ).Min();
			if ( enemyDistance < MinSpawnDistanceFromPlayers )
				continue;
			if ( bots.Any( x => x.WorldPosition.Distance( point ) < (IsEnemy( team, x.Team ) ? MinSpawnDistanceFromBots : MinSpawnDistanceFromTeammates) ) )
				continue;
			// Roofs are navmesh islands (Flatgrass's building has one): a bot spawned up there can't come down, and the
			// bots going after it pile up underneath.
			if ( Scene.NavMesh.CalculatePath( new Sandbox.Navigation.CalculatePathRequest { Start = point, Target = anchor.WorldPosition } ).Status
				!= Sandbox.Navigation.NavMeshPathStatus.Complete )
				continue;

			var anchorDistance = anchors.Min( x => x.WorldPosition.Distance( point ) );
			var score = -MathF.Abs( anchorDistance - wantedDistance );
			var mateDistance = bots.Where( x => !IsEnemy( team, x.Team ) ).Select( x => x.WorldPosition.Distance( point ) )
				.DefaultIfEmpty( float.MaxValue ).Min();
			score -= MathF.Max( 0f, MinSpawnDistanceFromTeammates * 2f - mateDistance );
			// Popping up in plain sight looks wrong, and more so right in front of them.
			foreach ( var enemy in enemies )
			{
				if ( !CanSee( enemy, point ) )
					continue;

				score -= 1500f;
				if ( Vector3.GetAngle( enemy.EyeAngles.Forward.WithZ( 0f ), (point - enemy.WorldPosition).WithZ( 0f ) ) < 60f )
					score -= 1500f;
			}

			candidates.Add( (point, score) );
		}

		if ( candidates.Count == 0 )
			return false;

		var chosen = Random.Shared.FromArray( candidates.OrderByDescending( x => x.Score ).Take( 3 ).ToArray() );
		transform = new Transform( chosen.Position, Rotation.Identity );
		return true;
	}

	private static bool IsEnemy( Team team, Team other ) =>
		GameUtils.IsFreeForAllMode || team == Team.Unassigned || (other != team && other != Team.Unassigned);

	private bool CanSee( PlayerPawn player, Vector3 position ) => !Scene.Trace.Ray( player.EyePosition, position + Vector3.Up * 48f )
		.WithoutTags( "player", "trigger", "playerclip", BotTag, BreakableGlass.Tag )
		.Run().Hit;

	/// <summary>
	/// Pick a free map-authored spawn (info_player_start) that no living player is standing near, but that one is
	/// within <see cref="MaxSpawnDistanceFromPlayers"/> of.
	/// </summary>
	private bool TryGetMapSpawn( out Transform transform )
	{
		transform = global::Transform.Zero;

		var players = GameUtils.PlayerPawns
			.Where( x => x.IsValid() && x.HealthComponent.State == LifeState.Alive )
			.Select( x => x.WorldPosition )
			.ToArray();
		var bots = Bots
			.Where( x => x.IsValid() && x.IsAlive )
			.Select( x => x.WorldPosition )
			.ToArray();

		var candidates = Scene.GetAllComponents<SpawnPoint>()
			.Select( x => x.Transform.World )
			.Where( t => players.All( p => p.Distance( t.Position ) > MapSpawnMinPlayerDistance ) )
			.Where( t => players.Length == 0 || players.Any( p => p.Distance( t.Position ) < MaxSpawnDistanceFromPlayers ) )
			.Where( t => bots.All( b => b.Distance( t.Position ) > MinSpawnDistanceFromBots ) )
			.Where( t => IsOnMainNavMesh( t.Position ) )
			.ToArray();

		if ( candidates.Length == 0 ) return false;

		transform = Random.Shared.FromArray( candidates ).WithScale( 1f );
		return true;
	}

	private Dictionary<Vector3, bool> _onMainNavMesh;

	/// <summary>
	/// Whether a bot here can walk to the team spawns. Roofs are navmesh islands: a bot spawned on Flatgrass's building
	/// (where all the map's own starts are) can't come down, and the bots going after it pile up underneath. Spawn
	/// points don't move, so each is only worked out once.
	/// </summary>
	private bool IsOnMainNavMesh( Vector3 position )
	{
		_onMainNavMesh ??= new();
		if ( _onMainNavMesh.TryGetValue( position, out var known ) )
			return known;

		var teamSpawn = Scene.GetAllComponents<TeamSpawnPoint>().FirstOrDefault();
		if ( !teamSpawn.IsValid() || Scene.NavMesh.GetClosestPoint( teamSpawn.WorldPosition, 100f ) is not { } target )
			return true;

		if ( Scene.NavMesh.GetClosestPoint( position, 100f ) is not { } start )
			return false;

		return _onMainNavMesh[position] = Scene.NavMesh.CalculatePath( new Sandbox.Navigation.CalculatePathRequest { Start = start, Target = target } )
			.Status == Sandbox.Navigation.NavMeshPathStatus.Complete;
	}

	private float GetSpawnScore( Vector3 position )
	{
		var playerDistance = GameUtils.PlayerPawns
			.Where( x => x.IsValid() && x.HealthComponent.State == LifeState.Alive )
			.Select( x => x.WorldPosition.Distance( position ) )
			.DefaultIfEmpty( MinSpawnDistanceFromPlayers )
			.Min();

		var botDistance = Bots
			.Where( x => x.IsValid() && x.IsAlive )
			.Select( x => x.WorldPosition.Distance( position ) )
			.DefaultIfEmpty( MinSpawnDistanceFromBots )
			.Min();

		return playerDistance + botDistance * 0.5f;
	}
}
