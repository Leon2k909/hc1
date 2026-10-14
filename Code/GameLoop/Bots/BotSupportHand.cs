namespace Facepunch;

/// <summary>Fits the support arm to this frame's weapon pose after animation, without evaluating the graph twice.</summary>
public sealed class BotSupportHand
{
	private readonly bool _right;
	public BotSupportHand( bool right = false ) { _right = right; }
	private Model _model;
	private int _upper = -1, _lower = -1, _hand = -1;
	private int[] _bones = Array.Empty<int>();
	private int[] _segments = Array.Empty<int>();
	private Transform[] _pose = Array.Empty<Transform>();
	private readonly List<SkinnedModelRenderer> _garments = new();
	private SkinnedModelRenderer _body;

	/// <summary>Keep a grip inside this arm's reach, leaving a small bend at the elbow.</summary>
	public Vector3 Reachable( SkinnedModelRenderer body, Vector3 target )
	{
		if ( !body.IsValid() || !body.SceneModel.IsValid() || body.Model is null ) return target;
		if ( _model != body.Model || _body != body ) Build( body );
		if ( _hand < 0 ) return target;
		var upper = body.SceneModel.GetBoneWorldTransform( _upper ).Position;
		var lower = body.SceneModel.GetBoneWorldTransform( _lower ).Position;
		var hand = body.SceneModel.GetBoneWorldTransform( _hand ).Position;
		var reach = upper.Distance( lower ) + lower.Distance( hand ) - .15f;
		var offset = target - upper;
		return offset.Length > reach ? upper + offset.Normal * reach : target;
	}

	public bool Apply( SkinnedModelRenderer body, Transform target, float weight = 1f )
		=> ApplyCore( body, target, weight, null, 0f );

	/// <summary>Use an anatomical elbow direction while fading from the animated arm's bend.</summary>
	public bool ApplyWithPole( SkinnedModelRenderer body, Transform target, Vector3 pole, float weight = 1f, float poleWeight = 1f )
		=> ApplyCore( body, target, weight, pole, poleWeight );

	private bool ApplyCore( SkinnedModelRenderer body, Transform target, float weight, Vector3? elbowPole, float poleWeight )
	{
		if ( !body.IsValid() || !body.SceneModel.IsValid() || body.Model is null || weight <= 0f ) return false;
		if ( _model != body.Model || _body != body ) Build( body );
		if ( _hand < 0 ) return false;

		var scene = body.SceneModel;
		var upper = scene.GetBoneWorldTransform( _upper );
		var lower = scene.GetBoneWorldTransform( _lower );
		var hand = scene.GetBoneWorldTransform( _hand );
		var wrist = Vector3.Lerp( hand.Position, target.Position, weight.Clamp( 0f, 1f ) );
		var rotation = Rotation.Lerp( hand.Rotation, target.Rotation, weight.Clamp( 0f, 1f ) );
		var a = upper.Position.Distance( lower.Position );
		var b = lower.Position.Distance( hand.Position );
		var to = wrist - upper.Position;
		if ( a < .001f || b < .001f || to.IsNearZeroLength ) return false;

		// Keep the animated elbow's bend direction and the original arm lengths, including at full extension.
		var direction = to.Normal;
		var distance = to.Length.Clamp( MathF.Abs( a - b ) + .001f, a + b - .001f );
		wrist = upper.Position + direction * distance;
		var pole = lower.Position - upper.Position;
		if ( elbowPole is { } preferred ) pole = Vector3.Lerp( pole, preferred, poleWeight.Clamp( 0f, 1f ) );
		var bend = pole - direction * pole.Dot( direction );
		if ( bend.Length < .001f ) bend = upper.Rotation.Up - direction * upper.Rotation.Up.Dot( direction );
		if ( bend.Length < .001f ) bend = upper.Rotation.Right - direction * upper.Rotation.Right.Dot( direction );
		bend = bend.Normal;
		var along = (a * a + distance * distance - b * b) / (2f * distance);
		var elbow = upper.Position + direction * along + bend * MathF.Sqrt( MathF.Max( 0f, a * a - along * along ) );
		var solvedUpper = upper.WithRotation( Rotation.FromToRotation( lower.Position - upper.Position, elbow - upper.Position ) * upper.Rotation );
		var solvedLower = lower.WithPosition( elbow ).WithRotation( Rotation.FromToRotation( hand.Position - lower.Position, wrist - elbow ) * lower.Rotation );
		var solvedHand = hand.WithPosition( wrist ).WithRotation( rotation );

		// Read before writing: the engine may propagate a parent change to its children. Fingers and twist bones
		// keep their animation relative to the segment they belong to; no persistent bone overrides or bone objects.
		for ( var i = 0; i < _bones.Length; i++ ) _pose[i] = scene.GetBoneWorldTransform( _bones[i] );
		for ( var i = 0; i < _bones.Length; i++ )
		{
			var original = _segments[i] == 0 ? upper : _segments[i] == 1 ? lower : hand;
			var solved = _segments[i] == 0 ? solvedUpper : _segments[i] == 1 ? solvedLower : solvedHand;
			scene.SetBoneWorldTransform( _bones[i], solved.ToWorld( original.ToLocal( _pose[i] ) ) );
		}

		// Clothing was merged earlier in UpdateBones; its sleeves/gloves must use the corrected arm too.
		foreach ( var garment in _garments )
		{
			if ( !garment.IsValid() || !garment.Enabled || garment.BoneMergeTarget != body || !garment.SceneModel.IsValid() ) continue;
			garment.SceneModel.MergeBones( scene );
		}
		return true;
	}

	private void Build( SkinnedModelRenderer body )
	{
		_body = body;
		_model = body.Model;
		var bones = _model.Bones;
		_hand = (_right ? bones.GetBone( "hand_R" ) ?? bones.GetBone( "r_hand" )
			: bones.GetBone( "hand_L" ) ?? bones.GetBone( "l_hand" ))?.Index ?? -1;
		_lower = _hand < 0 ? -1 : _model.GetBoneParent( _hand );
		_upper = _lower < 0 ? -1 : _model.GetBoneParent( _lower );
		if ( _upper < 0 ) { _hand = -1; return; }
		var selected = bones.AllBones.Where( b => Under( b.Index, _upper ) ).OrderBy( b => Depth( b.Index ) ).Select( b => b.Index ).ToArray();
		_bones = selected;
		_segments = selected.Select( i => Under( i, _hand ) ? 2 : Under( i, _lower ) ? 1 : 0 ).ToArray();
		_pose = new Transform[selected.Length];
		_garments.Clear();
		foreach ( var renderer in body.GetComponentsInChildren<SkinnedModelRenderer>( true ) )
			if ( renderer != body && renderer.BoneMergeTarget == body ) _garments.Add( renderer );
	}

	private bool Under( int bone, int ancestor )
	{
		for ( var i = bone; i >= 0; i = _model.GetBoneParent( i ) )
			if ( i == ancestor ) return true;
		return false;
	}

	private int Depth( int bone )
	{
		var depth = 0;
		for ( var i = _model.GetBoneParent( bone ); i >= 0; i = _model.GetBoneParent( i ) ) depth++;
		return depth;
	}
}
