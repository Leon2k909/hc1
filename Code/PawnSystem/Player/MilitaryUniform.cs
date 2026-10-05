namespace Facepunch;

/// <summary>Which outfit a soldier wears (<see cref="OperatorOutfits"/>). Saved in prefabs by number: add new ones last.</summary>
public enum MilitaryUniformStyle { Standard, Field, Tactical }

/// <summary>Team military uniforms using the realistic human clothing variants.</summary>
public sealed class MilitaryUniform : Component
{
	public const string HumanModelPath = "models/citizen_human/citizen_human_male.vmdl";
	public const string LegacyPoliceModelPath = "models/player/ct_side/ct_side_player_01/ct_side_player_01_v2.vmdl";
	public static readonly string[] ClothingPaths =
	{
		"models/citizen_clothes/hat/tactical_helmet/tactical_helmet_army.clothing",
		"models/citizen_clothes/shirt/army_shirt/army_shirt.clothing",
		"models/citizen_clothes/trousers/cargopants/cargo_pants_army.clothing",
		"models/citizen_clothes/vest/tactical_vest/models/tactical_vest_army.clothing",
		"models/citizen_clothes/shoes/boots/army_boots.clothing"
	};
	public static readonly string[] FieldClothingPaths = ClothingPaths.Append(
		"models/citizen_clothes/gloves/fingerless_gloves/fingerless_gloves.clothing" ).ToArray();
	/// <summary>
	/// A counter-terror team's dark kit: the army garments dyed (<see cref="TacticalTint"/>), with a balaclava under the
	/// helmet. The army pieces are used rather than the police helmet and vest because their colours are known, so the
	/// tints could be worked out from the Military Operator's portrait.
	/// </summary>
	public static readonly string[] TacticalClothingPaths = FieldClothingPaths.Append(
		"models/citizen_clothes/hat/balaclava/balaclava.clothing" ).ToArray();
	[Property] public MilitaryUniformStyle Style { get; set; }
	[Property] public List<Clothing> Pieces { get; set; } = new();
	[Property] public List<Clothing> FieldPieces { get; set; } = new();
	[Property] public List<Clothing> TacticalPieces { get; set; } = new();
	private Model dressedModel;
	private MilitaryUniformStyle dressedStyle;
	private bool dressed;
	private List<Clothing> wornPieces = new();
	private bool legsOnly;

	public static bool IsPoliceModel( Model model ) => model?.Name?.StartsWith( "models/player/ct_side/", StringComparison.OrdinalIgnoreCase ) == true;
	public static bool IsFieldModel( Model model ) => model?.Name?.StartsWith( "models/player/t_side/", StringComparison.OrdinalIgnoreCase ) == true;
	public static bool IsLegacyModel( Model model ) => IsPoliceModel( model ) || IsFieldModel( model );
	public static Model ResolveModel( Model model ) => IsLegacyModel( model ) ? Model.Load( HumanModelPath ) : model;
	public static MilitaryUniformStyle StyleForTeam( Team team ) => team == Team.CounterTerrorist ? MilitaryUniformStyle.Standard : MilitaryUniformStyle.Field;
	public static bool UsesHumanSkeleton( Model model ) => model?.Name == HumanModelPath;
	private static Transform? humanWristAxesOffset;
	public static Transform WeaponHandOffset( Model model )
	{
		var legacyOffset = LightweightCombatBot.HandHoldOffset;
		if ( !UsesHumanSkeleton( model ) ) return legacyOffset;
		// World weapon prefabs were authored for the old hand socket, not the human rig's hold_R socket.
		// Convert the wrist axes, not the bind-pose wrist positions: the two bodies have different arm lengths
		// and rest poses. Their positional difference would push the grip out of the palm.
		if ( humanWristAxesOffset is null )
		{
			var oldHand = Model.Load( LegacyPoliceModelPath ).Bones.GetBone( "r_hand" ).LocalTransform;
			var newHand = model.Bones.GetBone( "hand_R" ).LocalTransform;
			humanWristAxesOffset = new Transform( Vector3.Zero, newHand.Rotation.Inverse * oldHand.Rotation ).ToWorld( legacyOffset );
		}
		// The human rifle pose closes its fingers below the wrist. Seat the pistol grip in that palm.
		return humanWristAxesOffset.Value.ToWorld( new Transform( new Vector3( 0f, 0f, 5f ) ) );
	}
	public static Transform HandIkTransform( Model model, string hand, Transform target )
	{
		if ( !UsesHumanSkeleton( model ) || (hand != "hand_left" && hand != "hand_right") ) return target;
		var left = hand == "hand_left";
		var oldBone = Model.Load( LegacyPoliceModelPath ).Bones.GetBone( left ? "l_hand" : "r_hand" );
		var newBone = model.Bones.GetBone( left ? "hand_L" : "hand_R" );
		return target.WithRotation( target.Rotation * oldBone.LocalTransform.Rotation.Inverse * newBone.LocalTransform.Rotation );
	}

	protected override void OnStart()
	{
		var renderer = GetComponent<SkinnedModelRenderer>();
		if ( renderer.IsValid() ) SetModel( renderer, renderer.Model );
	}

	public void Refresh()
	{
		var renderer = GetComponent<SkinnedModelRenderer>();
		if ( !renderer.IsValid() || renderer.Model is null ) return;
		if ( dressed && dressedModel == renderer.Model && dressedStyle == Style ) return;
		if ( renderer.Model.Name != HumanModelPath ) return;
		if ( dressed ) new ClothingContainer().Reset( renderer );

		var outfit = new ClothingContainer { PrefersHuman = true };
		var paths = Style switch
		{
			MilitaryUniformStyle.Field => FieldClothingPaths,
			MilitaryUniformStyle.Tactical => TacticalClothingPaths,
			_ => ClothingPaths
		};
		var assigned = Style switch
		{
			MilitaryUniformStyle.Field => FieldPieces,
			MilitaryUniformStyle.Tactical => TacticalPieces,
			_ => Pieces
		};
		var pieces = assigned.Count > 0 ? assigned : paths.Select( ResourceLibrary.Get<Clothing> ).ToList();
		// The wardrobe picker treats a shirt and vest as alternative tops. A uniform deliberately layers both.
		foreach ( var piece in pieces.Where( c => c.IsValid() ) )
			outfit.Clothing.Add( new ClothingContainer.ClothingEntry { Clothing = piece } );
		outfit.Apply( renderer );
		foreach ( var garment in renderer.GetComponentsInChildren<SkinnedModelRenderer>() )
		{
			if ( garment == renderer || garment.BoneMergeTarget != renderer ) continue;
			garment.GameObject.Flags |= GameObjectFlags.NotSaved | GameObjectFlags.NotNetworked;
			garment.RenderType = renderer.RenderType;
			if ( Style == MilitaryUniformStyle.Field )
			{
				var path = garment.Model?.Name ?? "";
				garment.Tint = path.Contains( "tactical_vest" ) || path.Contains( "tactical_helmet" )
					? new Color( .50f, .64f, .46f )
					: path.Contains( "boots" ) ? new Color( .46f, .50f, .43f )
					: path.Contains( "gloves" ) ? Color.White : new Color( .76f, .86f, .66f );
			}
			else if ( Style == MilitaryUniformStyle.Tactical )
			{
				garment.Tint = TacticalTint( garment.Model?.Name ?? "" );
			}
		}
		dressed = true;
		dressedModel = renderer.Model;
		dressedStyle = Style;
		wornPieces = pieces.Where( c => c.IsValid() ).ToList();
		if ( legsOnly ) HideAboveTheWaist( renderer );
	}

	/// <summary>
	/// The Tactical Operator's dye for each garment. A tint multiplies the garment's colour in linear space (the Field
	/// Operator's portrait matches its tints on the Military Operator's to within 2 sRGB steps), so each was worked out
	/// from the army garments' colours in the Military Operator's portrait (sRGB) to land on: a black helmet (33,33,35),
	/// a black plate carrier (36,36,38), dark grey camouflage (49,50,52 on the sleeves; the trousers take the same dye,
	/// as they're the same cloth), black boots (30,29,29) and, from the Field Operator's undyed brown leather ones,
	/// black gloves (30,27,27). The balaclava's own colour isn't known, so it's only darkened.
	/// </summary>
	public static Color TacticalTint( string modelPath )
	{
		if ( modelPath.Contains( "tactical_helmet" ) ) return new Color( .27f, .33f, .51f );
		if ( modelPath.Contains( "tactical_vest" ) ) return new Color( .24f, .32f, .54f );
		if ( modelPath.Contains( "boots" ) ) return new Color( .14f, .17f, .27f );
		if ( modelPath.Contains( "gloves" ) ) return new Color( .45f, .62f, .85f );
		if ( modelPath.Contains( "balaclava" ) ) return new Color( .6f, .6f, .62f );
		return new Color( .58f, .64f, 1f );
	}

	/// <summary>
	/// Leaves only the legs showing, for the first-person body (<see cref="PlayerBody.FirstPersonBody"/>). It stands a
	/// little behind the camera, and leaning into a walk brought its face into view. The head (with its eyes and jaw),
	/// chest and hands are hidden by bodygroup, and every garment that covers neither the legs nor the feet (the helmet,
	/// shirt, vest and gloves) is turned off. It holds through a change of uniform. The legacy player models hide their
	/// upper body with the first-person body's procedural spine bones instead.
	/// </summary>
	public void ShowLegsOnly()
	{
		if ( legsOnly ) return;
		legsOnly = true;
		var renderer = GetComponent<SkinnedModelRenderer>( true );
		if ( dressed && renderer.IsValid() ) HideAboveTheWaist( renderer );
	}

	private void HideAboveTheWaist( SkinnedModelRenderer renderer )
	{
		foreach ( var name in new[] { "Head", "Chest", "Hands" } )
		{
			// A group's last choice is its empty one.
			if ( renderer.Model?.Parts.Get( name ) is { } part )
				renderer.SetBodyGroup( name, part.Choices.Count - 1 );
		}

		var legwear = new HashSet<string>( StringComparer.OrdinalIgnoreCase );
		foreach ( var piece in wornPieces )
		{
			if ( (piece.HideBody & (Clothing.BodyGroups.Legs | Clothing.BodyGroups.Feet)) == 0 ) continue;
			foreach ( var path in new[] { piece.Model, piece.HumanAltModel, piece.HumanAltFemaleModel }
				.Concat( piece.ConditionalModels?.Values ?? Enumerable.Empty<string>() ) )
			{
				if ( !string.IsNullOrEmpty( path ) ) legwear.Add( path );
			}
		}

		foreach ( var garment in renderer.GetComponentsInChildren<SkinnedModelRenderer>( true ) )
		{
			if ( garment == renderer || garment.BoneMergeTarget != renderer ) continue;
			garment.Enabled = legwear.Contains( garment.Model?.Name ?? "" );
		}
	}

	/// <summary>Change the body while retaining authored weapon sockets across the two human skeletons.</summary>
	public static void SetModel( SkinnedModelRenderer renderer, Model selected, MilitaryUniformStyle? style = null )
	{
		if ( !renderer.IsValid() || selected is null ) return;
		if ( IsLegacyModel( selected ) ) style ??= IsFieldModel( selected ) ? MilitaryUniformStyle.Field : MilitaryUniformStyle.Standard;
		selected = ResolveModel( selected );
		var uniform = renderer.GetComponent<MilitaryUniform>( true ) ?? renderer.GameObject.AddComponent<MilitaryUniform>();
		if ( style.HasValue ) uniform.Style = style.Value;
		// Prefabs can already use the human mesh while still holding legacy animation or physics settings.
		if ( UsesHumanSkeleton( selected ) ) renderer.AnimationGraph = null;
		if ( renderer.GetComponent<ModelPhysics>( true ) is { } physics ) physics.Model = selected;
		if ( renderer.Model == selected ) { uniform.Refresh(); return; }

		var oldModel = renderer.Model;
		var sockets = new List<(GameObject Object, string Bone, Transform BindPose)>();
		var mounts = renderer.GetComponent<EquipmentMountPoints>( true );
		var objects = mounts?.MountPoints.SelectMany( m => m.GameObjects ).Where( g => g.IsValid() ).ToList() ?? new();
		var pawn = renderer.GetComponentInParent<PlayerPawn>( true );
		if ( pawn.IsValid() && pawn.HoldGameObject.IsValid()
			&& pawn.HoldGameObject.GetComponentInParent<SkinnedModelRenderer>() == renderer ) objects.Add( pawn.HoldGameObject );
		var podium = renderer.GetComponent<IdleAnimator>( true );
		if ( podium.IsValid() && podium.HoldObject.IsValid() ) objects.Add( podium.HoldObject );
		foreach ( var socket in objects.Distinct() )
		{
			var bone = oldModel?.Bones.GetBone( socket.Parent?.Name ?? "" );
			if ( bone is null ) bone = Model.Load( LegacyPoliceModelPath ).Bones.GetBone( socket.Parent?.Name ?? "" );
			if ( bone is null ) continue;
			sockets.Add( (socket, bone.Name, BindPose( bone ).ToWorld( socket.LocalTransform )) );
			socket.SetParent( renderer.GameObject, true );
		}

		if ( uniform.dressed ) new ClothingContainer().Reset( renderer );
		uniform.dressed = false;
		renderer.Model = selected;
		foreach ( var socket in sockets )
		{
			var bone = selected.Bones.GetBone( socket.Bone ) ?? selected.Bones.GetBone( OtherSkeletonName( socket.Bone ) );
			var parent = bone is null ? null : renderer.GetBoneObject( bone.Name );
			if ( !parent.IsValid() ) continue;
			socket.Object.SetParent( parent, false );
			socket.Object.LocalTransform = BindPose( bone ).ToLocal( socket.BindPose );
		}
		uniform.Refresh();
	}

	// The engine exposes these relative to the model root, not relative to the parent bone.
	private static Transform BindPose( BoneCollection.Bone bone ) => bone.LocalTransform;
	private static string OtherSkeletonName( string name ) => name switch
	{
		"spine1" => "spine_0", "spine2" => "spine_1", "spine3" => "spine_2",
		"r_hip" => "leg_upper_R", "l_hip" => "leg_upper_L", "r_hand" => "hand_R", "l_hand" => "hand_L",
		"spine_0" => "spine1", "spine_1" => "spine2", "spine_2" => "spine3",
		"leg_upper_R" => "r_hip", "leg_upper_L" => "l_hip", "hand_R" => "r_hand", "hand_L" => "l_hand",
		_ => name
	};
}
