namespace Facepunch;

/// <summary>
/// The player's own outfit on their first-person arms: the shirt's sleeves, the gloves and the bare skin, as their body
/// wears them in third person. The first-person arms' own mesh is hidden (its "arms" bodygroup), and in its place a copy
/// of the selected human body, dressed by its own <see cref="MilitaryUniform"/> in the
/// body's outfit, is posed from the first-person arms' bones every frame.
/// </summary>
/// <remarks>
/// The first-person arms are their own model, 0.2-0.35" thicker in the forearm than the body's, so sleeves drawn over
/// them poked through. Drawing the body's own arms instead keeps the garments fitted as they are in third person.
/// <list type="bullet">
/// <item>The two skeletons share their arm and finger bones' names and axes, so those take the first-person arms'
/// model-space transforms as they are.</item>
/// <item>The torso has no first-person bones, so it's held where a body's is behind its eyes: the eyes (between eye_L
/// and eye_R) at the camera, the body facing the way it looks, and every bone off the arms in its bind pose from there.
/// It used to follow the clavicles, but the ported guns' clips swing those about: the M18's bring them 4" forward when
/// aimed and 8" in its reloads, which put the shirt's collar and shoulders in front of the camera. Each clavicle still
/// takes the first-person arms' own, so the sleeves are where they were. Only the arms and hands are drawn: the Head,
/// Legs and Feet bodygroups are hidden, and every garment with no arm, hand or finger bones (the helmet, trousers,
/// boots).</item>
/// <item>The forearm's twist bones take the hand's turn about the forearm as the citizen's constraints do (twist0
/// none of it, twist1 two thirds), and the elbow helper sits half way between the upper arm and the forearm.</item>
/// <item>The pose goes in as bone overrides in model space, as <see cref="SwbArmsRetarget"/>'s does, in
/// <see cref="ICameraSetup.LateSetup"/>, after the arm posers in PostSetup (SwbArmsRetarget, the tablet's, the
/// defuse kit's, the throwables' grip).</item>
/// </list>
/// </remarks>
public sealed partial class ViewModelClothing : Component, ICameraSetup
{
	/// <summary>The first-person arms the outfit follows.</summary>
	[Property] public SkinnedModelRenderer Arms { get; set; }

	/// <summary>The player's body, whose outfit is copied.</summary>
	[Property] public SkinnedModelRenderer Body { get; set; }

	/// <summary>Adds it to a freshly made viewmodel. It dresses once the body wears a uniform.</summary>
	public static void Fit( ViewModel viewModel, PlayerPawn player )
	{
		var arms = viewModel?.Arms;
		var body = player?.Body?.Renderer;
		if ( !arms.IsValid() || !body.IsValid() ) return;
		var clothing = viewModel.GameObject.AddComponent<ViewModelClothing>();
		clothing.Arms = arms;
		clothing.Body = body;
	}

	static readonly string[] HiddenParts = { "Head", "Legs", "Feet" };
	const string ArmsPart = "arms";

	enum Kind { Follow, Copy, Torso, Twist, Helper }

	sealed class Rig
	{
		public Kind[] Kinds;
		public int[] Order, Parent, From;
		public Transform[] Bind, BindLocal, Pose;
		public int Spine;

		// The eyes' bind pose (between eye_L and eye_R, facing +X), which the camera stands in for.
		public Transform Eyes;

		// Per bone, for twists and helpers: the forearm, the hand, the upper arm and the twist weight.
		public int[] Lower, Hand, Upper;
		public float[] Weight;
		public Vector3[] ForearmAxis;
	}

	sealed class Layer
	{
		public SkinnedModelRenderer Renderer;
		public int[] Map;
		public Transform[] Bind;
	}

	GameObject _root;
	SkinnedModelRenderer _skin;
	readonly List<Layer> _layers = new();
	// Posed with the layers but left their own materials: FirstPersonGrime's skins over them.
	readonly List<Layer> _followers = new();
	Model _dressedModel;
	MilitaryUniformStyle _dressedStyle;
	int? _armsChoice;
	TimeSince _sinceChecked = 1f;

	Rig _rig;
	Model _rigArms, _rigBody;
	Transform[] _source;
	Transform[] _poseWorld;

	protected override void OnUpdate()
	{
		if ( !Arms.IsValid() || !Body.IsValid() ) return;
		if ( _sinceChecked > 0.5f )
		{
			_sinceChecked = 0;
			var uniform = Body.GetComponent<MilitaryUniform>( true );
				var wearsUniform = uniform.IsValid() && MilitaryUniform.UsesHumanSkeleton( Body.Model );
			if ( !wearsUniform ) Undress();
			else if ( !_root.IsValid() || _dressedModel != Body.Model || _dressedStyle != uniform.Style ) Dress( uniform );
			foreach ( var layer in _layers ) ApplyDetailedMaterials( layer.Renderer );
		}

		// The tablet hides the arms while it flies the drone.
		if ( _root.IsValid() ) _root.Enabled = Arms.Enabled && Arms.Active;
	}

	protected override void OnDisabled() => Undress();

	protected override void OnDestroy() => Undress();

	void Dress( MilitaryUniform from )
	{
		Undress();
		if ( Arms.Model?.Parts.Get( ArmsPart ) is not { } armsPart || armsPart.Choices.Count < 2 ) return;

		_dressedModel = Body.Model;
		_dressedStyle = from.Style;

		_root = new GameObject( Arms.GameObject, true, "Clothing" );
		_root.Flags |= GameObjectFlags.NotSaved | GameObjectFlags.NotNetworked;
		_root.LocalTransform = global::Transform.Zero;

		_skin = _root.AddComponent<SkinnedModelRenderer>();
		_skin.UseAnimGraph = false;
		_skin.Model = Body.Model;
		Overlay( _skin );

		var uniform = _root.AddComponent<MilitaryUniform>();
		uniform.Style = from.Style;
		uniform.Pieces = from.Pieces.ToList();
		uniform.FieldPieces = from.FieldPieces.ToList();
		uniform.TacticalPieces = from.TacticalPieces.ToList();
		uniform.MilitiaPieces = from.MilitiaPieces.ToList();
		uniform.Refresh();

		foreach ( var name in HiddenParts )
		{
			// A group's last choice is its empty one.
			if ( _skin.Model.Parts.Get( name ) is { } part ) _skin.SetBodyGroup( name, part.Choices.Count - 1 );
		}

		_layers.Add( new Layer { Renderer = _skin } );
		foreach ( var garment in _root.GetComponentsInChildren<SkinnedModelRenderer>( true ) )
		{
			if ( garment == _skin ) continue;
			if ( !CoversArms( garment.Model ) )
			{
				garment.Enabled = false;
				continue;
			}
			// Posed here, with the body, rather than bone-merged a frame behind it.
			garment.BoneMergeTarget = null;
			garment.UseAnimGraph = false;
			garment.GameObject.LocalTransform = global::Transform.Zero;
			Overlay( garment );
			ApplyDetailedMaterials( garment );
			_layers.Add( new Layer { Renderer = garment } );
		}

		_armsChoice = Arms.GetBodyGroup( ArmsPart );
		Arms.SetBodyGroup( ArmsPart, armsPart.Choices.Count - 1 );
	}

	void Undress()
	{
		if ( _armsChoice is { } choice && Arms.IsValid() ) Arms.SetBodyGroup( ArmsPart, choice );
		_armsChoice = null;
		_root?.Destroy();
		_root = null;
		_skin = null;
		_layers.Clear();
		_followers.Clear();
		_dressedModel = null;
	}

	// Drawn as the viewmodel is: on the overlay layer, with no shadow.
	void Overlay( ModelRenderer renderer )
	{
		renderer.RenderOptions.Game = Arms.RenderOptions.Game;
		renderer.RenderOptions.Overlay = Arms.RenderOptions.Overlay;
		renderer.RenderType = Arms.RenderType;
	}

	static bool CoversArms( Model model )
	{
		if ( model is null ) return false;
		for ( int i = 0; i < model.BoneCount; i++ )
		{
			var name = model.GetBoneName( i );
			if ( name.StartsWith( "arm_" ) || name.StartsWith( "hand_" ) || name.StartsWith( "finger_" ) ) return true;
		}
		return false;
	}

	// Every camera in the scene runs this, so only the player's view (not a scope's lens or the minimap) places the body.
	void ICameraSetup.LateSetup( CameraComponent cc )
	{
		if ( cc.IsMainCamera ) Apply( cc.WorldTransform );
	}

	/// <param name="eye">The camera's world transform, where the body's eyes go.</param>
	void Apply( Transform eye )
	{
		if ( !_root.IsValid() || !_root.Active || !_skin.IsValid() || _skin.Model is null || Arms.Model is null ) return;
		var from = Arms.SceneModel;
		var to = _skin.SceneModel;
		if ( !from.IsValid() || !to.IsValid() ) return;

		if ( _rigArms != Arms.Model || _rigBody != _skin.Model )
		{
			_rigArms = Arms.Model;
			_rigBody = _skin.Model;
			_rig = Build( _rigArms, _rigBody );
			foreach ( var layer in _layers ) layer.Map = null;
			foreach ( var layer in _followers ) layer.Map = null;
			if ( _rig is null ) Log.Warning( $"ViewModelClothing: can't pose {_rigBody.Name} from {_rigArms.Name}" );
		}
		if ( _rig is null ) return;

		// Work in the body's model space (GetBoneLocalTransform is parent space, so go through world space).
		var rig = _rig;
		// The camera places the viewmodel during PreRender, before the renderers have necessarily copied their new
		// GameObject transforms to their SceneModels. Pose in this frame's space: using the cached render transform
		// for the eye adds the player's movement to the torso again when the renderer catches up (visible on jumps).
		var space = _skin.WorldTransform;
		var armsSpace = Arms.WorldTransform;
		var sourceSpace = from.Transform;
		var armsBones = _rigArms.BoneCount;
		if ( _source?.Length != armsBones ) _source = new Transform[armsBones];
		for ( int i = 0; i < armsBones; i++ )
		{
			var pose = sourceSpace.ToLocal( from.GetBoneWorldTransform( i ) );
			_source[i] = space.ToLocal( armsSpace.ToWorld( pose ) );
		}

		Solve( rig, space.ToLocal( eye ) );

		var count = rig.Pose.Length;
		if ( _poseWorld?.Length != count ) _poseWorld = new Transform[count];
		for ( int i = 0; i < count; i++ ) _poseWorld[i] = space.ToWorld( rig.Pose[i] );

		// The engine re-poses a model from its bind pose whenever the viewmodel moves, so the pose also goes in as bone
		// overrides (model space), which that re-pose keeps.
		var spine = rig.Pose[rig.Spine].ToWorld( rig.Bind[rig.Spine].ToLocal( global::Transform.Zero ) );
		foreach ( var layer in _layers ) Pose( layer, space, spine );
		foreach ( var layer in _followers ) Pose( layer, space, spine );
	}

	void Pose( Layer layer, Transform space, Transform spine )
	{
		if ( !layer.Renderer.IsValid() || layer.Renderer.Model is null ) return;
		var model = layer.Renderer.SceneModel;
		if ( !model.IsValid() ) return;
		if ( layer.Map is null ) Map( layer, _rigBody );
		var local = layer.Renderer.WorldTransform;
		model.Transform = local;
		for ( int i = 0; i < layer.Map.Length; i++ )
		{
			// A bone the body doesn't have keeps its bind pose relative to the torso.
			var world = layer.Map[i] >= 0 ? _poseWorld[layer.Map[i]] : space.ToWorld( spine.ToWorld( layer.Bind[i] ) );
			var pose = local.ToLocal( world );
			model.SetBoneOverride( i, pose );
			model.SetBoneWorldTransform( i, world );
		}
	}

	/// <summary>Whether this is one of the outfit's own renderers, posed here every frame.</summary>
	internal bool Poses( SkinnedModelRenderer renderer ) => _layers.Any( l => l.Renderer == renderer );

	/// <summary>
	/// Pose <paramref name="renderer"/> (a copy of one of the outfit's models) with the outfit, leaving its materials
	/// alone: FirstPersonGrime's skin over a sleeve or glove. Dropped when the outfit changes.
	/// </summary>
	internal void Follow( SkinnedModelRenderer renderer )
	{
		_followers.RemoveAll( l => !l.Renderer.IsValid() || l.Renderer == renderer );
		_followers.Add( new Layer { Renderer = renderer } );
	}

	/// <param name="eye">The camera in the body's model space.</param>
	void Solve( Rig rig, Transform eye )
	{
		// The torso: the body's eyes at the camera, facing the way it looks.
		var torso = new Transform( eye.Position, eye.Rotation ).ToWorld( rig.Eyes.ToLocal( global::Transform.Zero ) );

		for ( int i = 0; i < rig.Pose.Length; i++ )
		{
			if ( rig.Kinds[i] == Kind.Copy ) rig.Pose[i] = _source[rig.From[i]];
			else if ( rig.Kinds[i] == Kind.Torso ) rig.Pose[i] = torso.ToWorld( rig.Bind[i] );
		}

		foreach ( var i in rig.Order )
		{
			switch ( rig.Kinds[i] )
			{
				case Kind.Twist:
					rig.Pose[i] = Twist( rig, i );
					break;
				case Kind.Helper:
					rig.Pose[i] = Helper( rig, i );
					break;
				case Kind.Follow:
					var parent = rig.Parent[i];
					rig.Pose[i] = parent >= 0 ? rig.Pose[parent].ToWorld( rig.BindLocal[i] ) : torso.ToWorld( rig.Bind[i] );
					break;
			}
		}
	}

	/// <summary>
	/// A forearm twist bone: along the forearm where its bind pose has it, turned by its share of the hand's turn about
	/// the forearm.
	/// </summary>
	static Transform Twist( Rig rig, int i )
	{
		int lower = rig.Lower[i], hand = rig.Hand[i];
		var lowerPose = rig.Pose[lower];
		var handPose = rig.Pose[hand];
		var lowerBind = rig.Bind[lower];
		var handBind = rig.Bind[hand];

		// How far along the forearm it sits.
		var along = handBind.Position - lowerBind.Position;
		var fraction = Vector3.Dot( rig.Bind[i].Position - lowerBind.Position, along ) / along.LengthSquared;
		var position = lowerPose.Position + (handPose.Position - lowerPose.Position) * fraction;

		// The hand's turn from its bind pose, in the forearm's frame, and of that only the part about the forearm.
		var turn = lowerPose.Rotation.Inverse * handPose.Rotation * (lowerBind.Rotation.Inverse * handBind.Rotation).Inverse;
		var twist = TwistAbout( turn, rig.ForearmAxis[i] );
		var rotation = lowerPose.Rotation * Rotation.Slerp( Rotation.Identity, twist, rig.Weight[i] )
			* (lowerBind.Rotation.Inverse * rig.Bind[i].Rotation);
		return new Transform( position, rotation );
	}

	/// <summary>The twist part of a swing-twist split of <paramref name="rotation"/> about <paramref name="axis"/>.</summary>
	static Rotation TwistAbout( Rotation rotation, Vector3 axis )
	{
		var along = Vector3.Dot( new Vector3( rotation.x, rotation.y, rotation.z ), axis );
		var twist = new Rotation( axis.x * along, axis.y * along, axis.z * along, rotation.w );
		var length = MathF.Sqrt( along * along + rotation.w * rotation.w );
		if ( length < 0.0001f ) return Rotation.Identity;
		twist = new Rotation( twist.x / length, twist.y / length, twist.z / length, twist.w / length );
		return twist;
	}

	/// <summary>The elbow helper: half way between the upper arm's turn and the forearm's, at the elbow.</summary>
	static Transform Helper( Rig rig, int i )
	{
		int upper = rig.Upper[i], lower = rig.Lower[i];
		var upperBind = rig.Bind[upper];
		var lowerBind = rig.Bind[lower];
		var lowerPose = rig.Pose[lower];
		var straight = rig.Pose[upper].Rotation * (upperBind.Rotation.Inverse * lowerBind.Rotation);
		var rotation = Rotation.Slerp( straight, lowerPose.Rotation, 0.5f ) * (lowerBind.Rotation.Inverse * rig.Bind[i].Rotation);
		var position = lowerPose.PointToWorld( lowerBind.PointToLocal( rig.Bind[i].Position ) );
		return new Transform( position, rotation );
	}

	static Rig Build( Model arms, Model body )
	{
		var count = body.BoneCount;
		var rig = new Rig
		{
			Kinds = new Kind[count],
			Parent = new int[count],
			From = new int[count],
			Bind = new Transform[count],
			BindLocal = new Transform[count],
			Pose = new Transform[count],
			Lower = new int[count],
			Hand = new int[count],
			Upper = new int[count],
			Weight = new float[count],
			ForearmAxis = new Vector3[count],
			Spine = BoneIndex( body, "spine_2" ),
		};
		int eyeL = BoneIndex( body, "eye_L" ), eyeR = BoneIndex( body, "eye_R" );
		if ( rig.Spine < 0 || eyeL < 0 || eyeR < 0 || BoneIndex( arms, "clavicle_R" ) < 0 || BoneIndex( arms, "clavicle_L" ) < 0 ) return null;

		for ( int i = 0; i < count; i++ )
		{
			var parent = body.GetBoneParent( i );
			rig.Parent[i] = parent;
			rig.Bind[i] = body.GetBoneTransform( i );
			rig.BindLocal[i] = parent >= 0 ? body.GetBoneTransform( parent ).ToLocal( rig.Bind[i] ) : rig.Bind[i];
			rig.From[i] = rig.Lower[i] = rig.Hand[i] = rig.Upper[i] = -1;
		}
		rig.Eyes = new Transform( (rig.Bind[eyeL].Position + rig.Bind[eyeR].Position) * 0.5f, Rotation.Identity );

		// Parents before children.
		rig.Order = Enumerable.Range( 0, count ).OrderBy( i => Depth( body, i ) ).ToArray();

		for ( int i = 0; i < count; i++ )
		{
			var name = body.GetBoneName( i );
			var side = ArmSide( body, i );
			if ( side is null )
			{
				rig.Kinds[i] = Kind.Torso;
				continue;
			}

			var lower = BoneIndex( body, "arm_lower_" + side );
			var hand = BoneIndex( body, "hand_" + side );
			var upper = BoneIndex( body, "arm_upper_" + side );
			var special = name.Contains( "_twist" ) || name.Contains( "helper" );
			var from = special ? -1 : BoneIndex( arms, name );
			if ( from >= 0 )
			{
				rig.Kinds[i] = Kind.Copy;
				rig.From[i] = from;
			}
			else if ( name.StartsWith( "arm_lower_" + side + "_twist" ) && lower >= 0 && hand >= 0 )
			{
				rig.Kinds[i] = Kind.Twist;
				rig.Lower[i] = lower;
				rig.Hand[i] = hand;
				// The citizen's twist constraints: twist0 takes none of the hand's turn, twist1 about two thirds.
				var along = rig.Bind[hand].Position - rig.Bind[lower].Position;
				rig.Weight[i] = name.EndsWith( "twist0" ) ? 0f
					: name.EndsWith( "twist1" ) ? 0.67f
					: Math.Clamp( Vector3.Dot( rig.Bind[i].Position - rig.Bind[lower].Position, along ) / along.LengthSquared, 0f, 1f );
				rig.ForearmAxis[i] = (rig.Bind[lower].Rotation.Inverse * along).Normal;
			}
			else if ( name.StartsWith( "arm_elbow_helper" ) && lower >= 0 && upper >= 0 )
			{
				rig.Kinds[i] = Kind.Helper;
				rig.Lower[i] = lower;
				rig.Upper[i] = upper;
			}
			else
			{
				rig.Kinds[i] = Kind.Follow;
			}
		}

		return rig;
	}

	/// <summary>"R" or "L" for a clavicle or a bone under one, else null.</summary>
	static string ArmSide( Model model, int bone )
	{
		for ( var b = bone; b >= 0; b = model.GetBoneParent( b ) )
		{
			var name = model.GetBoneName( b );
			if ( name == "clavicle_R" ) return "R";
			if ( name == "clavicle_L" ) return "L";
		}
		return null;
	}

	static void Map( Layer layer, Model body )
	{
		var model = layer.Renderer.Model;
		layer.Map = new int[model.BoneCount];
		layer.Bind = new Transform[model.BoneCount];
		for ( int i = 0; i < model.BoneCount; i++ )
		{
			layer.Map[i] = BoneIndex( body, model.GetBoneName( i ) );
			layer.Bind[i] = model.GetBoneTransform( i );
		}
	}

	static int BoneIndex( Model model, string name ) => name is not null && model.Bones.HasBone( name ) ? model.Bones.GetBone( name ).Index : -1;

	static int Depth( Model model, int bone )
	{
		var depth = 0;
		for ( var parent = model.GetBoneParent( bone ); parent >= 0; parent = model.GetBoneParent( parent ) ) depth++;
		return depth;
	}
}
