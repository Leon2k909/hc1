using Facepunch.Gunsmith;
using Sandbox.Events;

namespace Facepunch;

/// <summary>
/// Blood and dirt on the gun, gloves and sleeves the local player sees in first person. Getting shot puts blood on them
/// (most from a hit to the arms or hands, which bleed onto the grip), lying and crawling on the ground dirties them in
/// the ground's own colour (soil, mud, sand, grass, concrete dust), and rain or water washes it off again. Blood dries
/// from a wet red to a matte brown-black over a couple of minutes.
/// </summary>
/// <remarks>
/// <list type="bullet">
/// <item>Each gun keeps its own grime for the life, the hands theirs (sleeves and gloves together); a new life starts
/// clean.</item>
/// <item>It's drawn as a second skin over every renderer in the viewmodel (<see cref="GrimeSkin"/>): the same model,
/// bone-merged to it (or posed with the sleeves by <see cref="ViewModelClothing"/>), wearing
/// <c>materials/effects/hc1_grime.vmat</c> on every slot but lenses, reticles and hidden pieces. The shader pushes it a
/// hair out and draws the blood and dirt in the model's own space, so it sticks to the gun as it animates.</item>
/// <item>Only on this machine, for this player: nothing is networked, and the third-person gun stays clean.</item>
/// </list>
/// </remarks>
public sealed class FirstPersonGrime : Component, IGameEventHandler<DamageTakenEvent>
{
	/// <summary>The skin's material.</summary>
	public const string MaterialPath = "materials/effects/hc1_grime.vmat";

	/// <summary>Blood darkens and dries with this time constant, in seconds: mostly dry after two or three minutes.</summary>
	public const float BloodDryTime = 90f;

	/// <summary>Dirt a second lying still on soil (shifting your elbows), crawling over it, and sliding across it.</summary>
	public const float LyingRate = 0.004f, CrawlRate = 0.05f, SlideRate = 0.03f;

	/// <summary>Dropping prone on soil: the hands and forearms hit the ground.</summary>
	public const float DropDirt = 0.08f;

	/// <summary>The gun picks up this share of what the hands do: it's held off the ground more often than not.</summary>
	public const float GunShare = 0.5f;

	/// <summary>Rain washes off this much a second per mm/h, outdoors (5 mm/h rinses a gun in about two minutes); lying in water much faster.</summary>
	public const float RainWash = 0.0015f, WaterWash = 0.2f;

	/// <summary>Linear colours of the grounds' dirt.</summary>
	public static readonly Vector3 SoilColor = new( 0.155f, 0.09f, 0.045f ), MudColor = new( 0.075f, 0.045f, 0.024f ),
		SandColor = new( 0.48f, 0.36f, 0.2f ), GravelColor = new( 0.21f, 0.19f, 0.15f ), GrassColor = new( 0.09f, 0.1f, 0.035f ),
		DustColor = new( 0.3f, 0.28f, 0.24f ), GreaseColor = new( 0.045f, 0.04f, 0.036f );

	/// <summary>One thing's grime: a gun's, or the hands'.</summary>
	public sealed class Grime
	{
		public float Blood, Dirt, Mud;
		public Vector3 DirtColor = SoilColor;
		public TimeSince SinceBlood = 999f;
		public readonly float Seed = Game.Random.Float( 0f, 100f );

		public bool Visible => Blood > 0.005f || Dirt > 0.005f;
		public float Dry => 1f - MathF.Exp( -SinceBlood / BloodDryTime );

		public void AddBlood( float amount )
		{
			if ( amount <= 0f ) return;
			Blood = MathF.Min( 1f, Blood + amount );
			SinceBlood = 0f;
		}

		public void AddDirt( float amount, Vector3 colour, float mud )
		{
			if ( amount <= 0f ) return;
			// The dirt takes the colour of what's been added, by how much of it there is.
			var share = amount / (Dirt + amount);
			DirtColor = Vector3.Lerp( DirtColor, colour, share );
			Mud = MathX.Lerp( Mud, mud, share );
			Dirt = MathF.Min( 1f, Dirt + amount );
		}

		/// <summary>Dirt rinses off first; dried blood takes longer.</summary>
		public void Wash( float amount )
		{
			if ( amount <= 0f ) return;
			Dirt = MathF.Max( 0f, Dirt - amount );
			Blood = MathF.Max( 0f, Blood - amount * 0.6f );
		}
	}

	/// <summary>What a ground leaves on you: its dirt's colour, how fast it rubs off on you, how wet it is, or that it washes.</summary>
	public readonly record struct Ground( Vector3 Colour, float Rate, float Mud, bool Washes )
	{
		public static readonly Ground None = new( SoilColor, 0f, 0f, false );
	}

	private readonly Grime _hands = new();
	private readonly Dictionary<Equipment, Grime> _guns = new();
	private readonly Dictionary<ModelRenderer, ModelRenderer> _skins = new();
	private readonly List<ModelRenderer> _stale = new();
	private PlayerPawn _player;
	private ViewModel _viewModel;
	private Weather _weather;
	private Ground _ground = Ground.None;
	private TimeSince _sinceGround, _sinceSky = 99f, _sinceScan = 99f;
	private bool _outdoors, _wasLying, _wasAlive;
	private float _wet;
	private static Material _material, _hidden;

	private PlayerPawn Player => _player.IsValid() ? _player : _player = GetComponent<PlayerPawn>();

	/// <summary>The hands' grime: sleeves and gloves.</summary>
	public Grime Hands => _hands;

	/// <summary>A gun's grime, made clean the first time it's asked for. Null for no gun.</summary>
	public Grime For( Equipment equipment )
	{
		if ( !equipment.IsValid() ) return null;
		if ( !_guns.TryGetValue( equipment, out var grime ) ) _guns[equipment] = grime = new Grime();
		return grime;
	}

	protected override void OnUpdate()
	{
		var player = Player;
		if ( !player.IsValid() || !player.IsLocallyControlled ) return;

		var alive = player.HealthComponent.IsValid() && player.HealthComponent.State == LifeState.Alive;
		if ( alive && !_wasAlive ) Clean();
		_wasAlive = alive;
		if ( alive ) Accumulate( player );
		UpdateSkins( player );
	}

	protected override void OnDestroy()
	{
		foreach ( var skin in _skins.Values )
			if ( skin.IsValid() ) skin.GameObject.Destroy();
		_skins.Clear();
	}

	/// <summary>A new life starts clean: the hands, and every gun (they're new ones anyway).</summary>
	private void Clean()
	{
		_hands.Blood = _hands.Dirt = _hands.Mud = 0f;
		_guns.Clear();
		_wasLying = false;
	}

	/// <summary>
	/// dev_grime [blood] [dirt] [ground] [dry]: set the local player's hands and gun in hand to that much blood and dirt
	/// (0-1), the dirt from a ground (soil, mud, sand, gravel, grass, dust) and the blood that far dried (0-1).
	/// </summary>
	[ConCmd( "dev_grime" )]
	public static void DevGrime( float blood = 0.6f, float dirt = 0.5f, string ground = "soil", float dry = 0f )
	{
		var player = Client.Local?.PlayerPawn;
		var grime = player.IsValid() ? player.Components.Get<FirstPersonGrime>() : null;
		if ( !grime.IsValid() ) { Log.Warning( "dev_grime: no local player" ); return; }

		var (colour, mud) = ground.ToLowerInvariant() switch
		{
			"mud" => (MudColor, 1f),
			"sand" => (SandColor, 0f),
			"gravel" => (GravelColor, 0f),
			"grass" => (GrassColor, 0.2f),
			"dust" => (DustColor, 0f),
			_ => (SoilColor, 0f)
		};
		foreach ( var target in new[] { grime._hands, grime.For( player.CurrentEquipment ) } )
		{
			if ( target is null ) continue;
			target.Blood = blood.Clamp( 0f, 1f );
			// Dried that far: back-date the last bleed.
			target.SinceBlood = -BloodDryTime * MathF.Log( 1f - dry.Clamp( 0f, 0.999f ) );
			target.Dirt = dirt.Clamp( 0f, 1f );
			target.DirtColor = colour;
			target.Mud = mud;
		}
		Log.Info( $"dev_grime: blood {blood:0.##} ({dry:0.##} dry), {ground} dirt {dirt:0.##}" );
	}

	void IGameEventHandler<DamageTakenEvent>.OnGameEvent( DamageTakenEvent eventArgs ) => Bleed( eventArgs.DamageInfo );

	/// <summary>Blood from a hit: most from the arms and hands, which bleed onto the grip; a blast throws the ground up too.</summary>
	private void Bleed( DamageInfo info )
	{
		var player = Player;
		if ( !player.IsValid() || !player.IsLocallyControlled || info.Damage <= 0f || info.WasFallDamage
			|| info.Flags.HasFlag( DamageFlags.Burn ) || info.Flags.HasFlag( DamageFlags.Zone ) ) return;

		var amount = (info.Damage / 40f).Clamp( 0.4f, 1.5f );
		var gun = For( player.CurrentEquipment );
		float hands, onGun;
		if ( info.WasExplosion )
		{
			hands = 0.12f;
			onGun = 0.08f;
			var ground = GroundUnder( player );
			if ( !ground.Washes && ground.Rate > 0f )
			{
				_hands.AddDirt( 0.25f * amount, ground.Colour, ground.Mud );
				gun?.AddDirt( 0.2f * amount, ground.Colour, ground.Mud );
			}
		}
		else if ( (info.Hitbox & (HitboxTags.Arm | HitboxTags.Hand)) != 0 ) { hands = 0.45f; onGun = 0.3f; }
		else if ( (info.Hitbox & (HitboxTags.Leg | HitboxTags.Ankle)) != 0 ) { hands = 0.12f; onGun = 0.05f; }
		else { hands = 0.25f; onGun = 0.18f; }

		_hands.AddBlood( hands * amount );
		gun?.AddBlood( onGun * amount );
	}

	/// <summary>Dirt from the ground under you while lying, crawling or sliding; rain and water rinse it off.</summary>
	private void Accumulate( PlayerPawn player )
	{
		var dt = Time.Delta;
		var gun = For( player.CurrentEquipment );

		var lying = player.ProneBlend > 0.5f;
		var sliding = player.SlideBlend > 0.5f;
		if ( lying || sliding )
		{
			if ( _sinceGround > 0.2f )
			{
				_sinceGround = 0f;
				_ground = GroundUnder( player );
			}

			if ( _ground.Washes )
			{
				_hands.Wash( WaterWash * dt );
				gun?.Wash( WaterWash * dt );
			}
			else
			{
				var speed = player.CharacterController.IsValid() ? player.CharacterController.Velocity.WithZ( 0f ).Length : 0f;
				var rate = sliding ? SlideRate : speed > 15f ? CrawlRate * (speed / 55f).Clamp( 0.5f, 1.5f ) : LyingRate;
				var amount = rate * _ground.Rate * dt;
				if ( lying && !_wasLying ) amount += DropDirt * _ground.Rate;
				_hands.AddDirt( amount, _ground.Colour, _ground.Mud );
				gun?.AddDirt( amount * GunShare, _ground.Colour, _ground.Mud );
			}
		}
		_wasLying = lying;

		// Rain, outdoors: it rinses everything a little and wets it, and wet dirt turns to mud.
		if ( _sinceSky > 1f )
		{
			_sinceSky = 0f;
			if ( !_weather.IsValid() ) _weather = Scene.GetAllComponents<Weather>().FirstOrDefault();
			_outdoors = UnderSky( player );
		}
		var rain = _outdoors && _weather.IsValid() ? _weather.RainRate : 0f;
		_wet = rain > 0f ? MathF.Max( _wet, MathF.Min( 1f, rain / 4f ) ) : MathF.Max( 0f, _wet - dt / 60f );
		if ( rain > 0f )
		{
			_hands.Wash( rain * RainWash * dt );
			gun?.Wash( rain * RainWash * dt );
			_hands.Mud = MathF.Max( _hands.Mud, _wet * 0.8f );
			if ( gun is not null ) gun.Mud = MathF.Max( gun.Mud, _wet * 0.8f );
		}
	}

	/// <summary>The ground under the hands: a little ahead of the pawn, along the way the body lies.</summary>
	private Ground GroundUnder( PlayerPawn player )
	{
		var start = player.WorldPosition + Vector3.Up * 16f + Rotation.FromYaw( player.ProneYaw ).Forward * 12f;
		var tr = Scene.Trace.Ray( start, start - Vector3.Up * 40f )
			.IgnoreGameObjectHierarchy( player.GameObject )
			.WithoutTags( "player", "ragdoll", "movement", "playerclip", "corpse" )
			.Run();
		if ( !tr.Hit ) return Ground.None;
		if ( tr.GameObject is { } hit && hit.Tags.Has( "water" ) ) return new Ground( SoilColor, 0f, 0f, true );
		return GroundOf( WorldSounds.SurfaceAt( tr ) );
	}

	/// <summary>What a surface rubs off on you, by its name (or its base surfaces'), else by its kind.</summary>
	public static Ground GroundOf( Surface surface )
	{
		for ( var s = surface; s is not null; s = s.GetBaseSurface() )
		{
			var name = s.ResourceName?.ToLowerInvariant() ?? "";
			if ( name.Contains( "water" ) || name.Contains( "wade" ) || name.Contains( "slime" ) ) return new Ground( SoilColor, 0f, 0f, true );
			if ( name.Contains( "snow" ) || name.Contains( "ice" ) ) return new Ground( SoilColor, 0f, 0f, true );
			if ( name.Contains( "mud" ) ) return new Ground( MudColor, 1.6f, 1f, false );
			if ( name.Contains( "sand" ) ) return new Ground( SandColor, 0.9f, 0f, false );
			if ( name.Contains( "gravel" ) ) return new Ground( GravelColor, 0.6f, 0f, false );
			if ( name.Contains( "grass" ) || name.Contains( "foliage" ) || name.Contains( "leaves" ) ) return new Ground( GrassColor, 0.5f, 0.2f, false );
			if ( name.Contains( "dirt" ) || name.Contains( "soil" ) || name.Contains( "earth" ) ) return new Ground( SoilColor, 1f, 0f, false );
		}

		return WorldSounds.Classify( surface ) switch
		{
			WorldSounds.Material.Dirt => new Ground( SoilColor, 1f, 0f, false ),
			WorldSounds.Material.Grass => new Ground( GrassColor, 0.5f, 0.2f, false ),
			WorldSounds.Material.Masonry or WorldSounds.Material.Tile => new Ground( DustColor, 0.25f, 0f, false ),
			WorldSounds.Material.Wood or WorldSounds.Material.Fabric => new Ground( DustColor, 0.12f, 0f, false ),
			WorldSounds.Material.Metal or WorldSounds.Material.SheetMetal => new Ground( GreaseColor, 0.08f, 0f, false ),
			_ => new Ground( DustColor, 0.15f, 0f, false )
		};
	}

	/// <summary>Open sky over the head: nothing solid within 4000 units straight up but the sky itself.</summary>
	private bool UnderSky( PlayerPawn player )
	{
		var eye = player.WorldPosition + Vector3.Up * 60f;
		var tr = Scene.Trace.Ray( eye, eye + Vector3.Up * 4000f )
			.IgnoreGameObjectHierarchy( player.GameObject )
			.WithoutTags( "player", "trigger", "ragdoll", "movement", "playerclip", "water" )
			.Run();
		if ( !tr.Hit ) return true;
		var surface = tr.Surface?.ResourceName ?? "";
		return surface.Contains( "sky", StringComparison.OrdinalIgnoreCase ) || (tr.GameObject?.Tags.Has( "sky" ) ?? false);
	}

	/// <summary>Give every renderer in the viewmodel a skin, and keep each skin's grime and look in step with it.</summary>
	private void UpdateSkins( PlayerPawn player )
	{
		var viewModel = player.CurrentEquipment.IsValid() ? player.CurrentEquipment.ViewModel : null;
		if ( viewModel != _viewModel )
		{
			_viewModel = viewModel;
			_sinceScan = 99f;
		}

		var gun = For( player.CurrentEquipment );
		if ( viewModel.IsValid() && (_hands.Visible || (gun?.Visible ?? false)) && _sinceScan > 0.5f )
		{
			_sinceScan = 0f;
			Scan( viewModel );
		}

		_stale.Clear();
		foreach ( var (source, skin) in _skins )
		{
			if ( !source.IsValid() || !skin.IsValid() )
			{
				_stale.Add( source );
				continue;
			}
			var grime = IsHands( viewModel, source ) ? _hands : gun;
			Sync( source, skin, grime );
		}
		foreach ( var source in _stale )
		{
			if ( _skins.TryGetValue( source, out var skin ) && skin.IsValid() ) skin.GameObject.Destroy();
			_skins.Remove( source );
		}
	}

	private static bool IsHands( ViewModel viewModel, ModelRenderer source ) =>
		viewModel.IsValid() && (source == viewModel.Arms || source.GetComponentInParent<MilitaryUniform>( true ).IsValid());

	/// <summary>Make the skins this viewmodel's renderers are missing, and refresh which of their slots the grime covers.</summary>
	private void Scan( ViewModel viewModel )
	{
		_material ??= Material.Load( MaterialPath );
		_hidden ??= Material.Load( "attachments/m4a1/materials/hidden.vmat" );
		if ( _material is null || _material.IsError ) return;

		var clothing = viewModel.GameObject.Components.Get<ViewModelClothing>( FindMode.EverythingInSelfAndDescendants );
		foreach ( var source in viewModel.GameObject.Components.GetAll<ModelRenderer>( FindMode.EverythingInSelfAndDescendants ) )
		{
			if ( source.Model is null || source.Components.Get<GrimeSkin>( FindMode.EverythingInSelf ).IsValid() ) continue;
			if ( !_skins.TryGetValue( source, out var skin ) || !skin.IsValid() )
			{
				skin = MakeSkin( source, clothing );
				_skins[source] = skin;
			}
			Cover( source, skin );
		}
	}

	private static ModelRenderer MakeSkin( ModelRenderer source, ViewModelClothing clothing )
	{
		var go = new GameObject( source.GameObject, true, "Grime" );
		go.Flags |= GameObjectFlags.NotSaved | GameObjectFlags.NotNetworked;
		go.LocalTransform = global::Transform.Zero;
		go.AddComponent<GrimeSkin>().Source = source;

		ModelRenderer skin;
		if ( source is SkinnedModelRenderer skinned )
		{
			var renderer = go.AddComponent<SkinnedModelRenderer>( false );
			renderer.Model = skinned.Model;
			renderer.UseAnimGraph = false;
			// The sleeves and gloves are posed by ViewModelClothing, which poses their skins with them; the gun and its
			// parts are animated, and their skins follow their bones.
			if ( clothing.IsValid() && clothing.Poses( skinned ) ) clothing.Follow( renderer );
			else renderer.BoneMergeTarget = skinned;
			skin = renderer;
		}
		else
		{
			skin = go.AddComponent<ModelRenderer>( false );
			skin.Model = source.Model;
		}

		skin.RenderType = ModelRenderer.ShadowRenderType.Off;
		skin.RenderOptions.Game = source.RenderOptions.Game;
		skin.RenderOptions.Overlay = source.RenderOptions.Overlay;
		skin.RenderOptions.Bloom = source.RenderOptions.Bloom;
		skin.RenderOptions.AfterUI = source.RenderOptions.AfterUI;
		skin.BodyGroups = source.BodyGroups;
		skin.Enabled = true;
		return skin;
	}

	/// <summary>Grime on every slot but lenses, reticles, see-through parts and pieces the gunsmith has hidden.</summary>
	private static void Cover( ModelRenderer source, ModelRenderer skin )
	{
		var materials = source.Model.Materials;
		for ( var i = 0; i < materials.Length; i++ )
		{
			var shown = source.Materials.GetOverride( i ) ?? materials[i];
			var cover = Grimes( shown ) ? _material : _hidden;
			if ( skin.Materials.GetOverride( i ) != cover ) skin.Materials.SetOverride( i, cover );
		}
	}

	private static bool Grimes( Material material )
	{
		if ( material is null || material.IsError ) return false;
		var name = material.Name ?? "";
		if ( name.Contains( "nodraw", StringComparison.OrdinalIgnoreCase ) ) return false;
		if ( material.GetFeature( "F_TRANSLUCENT" ) == 1 || material.GetFeature( "F_ALPHA_TEST" ) == 1 ) return false;
		return CamoMaterialRules.Classify( name, material.ShaderName, false, false ) == CamoMaterialRules.Surface.Paintable;
	}

	private void Sync( ModelRenderer source, ModelRenderer skin, Grime grime )
	{
		var show = grime is not null && grime.Visible && source.Enabled && source.Active;
		if ( skin.Enabled != show ) skin.Enabled = show;
		if ( !show || !skin.SceneObject.IsValid() ) return;

		skin.SceneObject.RenderingEnabled = source.SceneObject.IsValid() && source.SceneObject.RenderingEnabled;
		if ( skin.BodyGroups != source.BodyGroups ) skin.BodyGroups = source.BodyGroups;
		// The viewmodel can move its renderers between the game and overlay layers after the skin was made.
		if ( skin.RenderOptions.Overlay != source.RenderOptions.Overlay ) skin.RenderOptions.Overlay = source.RenderOptions.Overlay;
		if ( skin.RenderOptions.Game != source.RenderOptions.Game ) skin.RenderOptions.Game = source.RenderOptions.Game;
		var attributes = skin.SceneObject.Attributes;
		attributes.Set( "GrimeBlood", grime.Blood );
		attributes.Set( "GrimeBloodDry", grime.Dry );
		attributes.Set( "GrimeDirt", grime.Dirt );
		attributes.Set( "GrimeDirtColor", grime.DirtColor );
		attributes.Set( "GrimeMud", grime.Mud );
		attributes.Set( "GrimeWet", _wet );
		attributes.Set( "GrimeSeed", grime.Seed );
	}
}

/// <summary>
/// Marks a <see cref="FirstPersonGrime"/> skin, so the gunsmith's camo and hidden-piece passes leave its material alone.
/// </summary>
public sealed class GrimeSkin : Component
{
	/// <summary>The renderer it covers.</summary>
	public ModelRenderer Source { get; set; }
}
