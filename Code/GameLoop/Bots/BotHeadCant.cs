namespace Facepunch;

/// <summary>
/// A cheek weld for a shouldered gun, applied after animation: the head cants its right ear down about the line of sight
/// through the sighting eye, so the eye stays on the sights while the jaw swings off the stock, and the neck turns to
/// meet it. Upright, with the right eye on a gun's centreline, the cheek and jaw went through the stock (a FAMAS's,
/// an AUG's, an M4's). The citizen graph has no head roll.
/// </summary>
public sealed class BotHeadCant
{
	private Model _model;
	private SkinnedModelRenderer _body;
	private int _neck = -1, _head = -1;
	private int[] _bones = Array.Empty<int>();
	private bool[] _inHead = Array.Empty<bool>();
	private Transform[] _pose = Array.Empty<Transform>();
	private readonly List<SkinnedModelRenderer> _garments = new();

	/// <summary> Cants the head <paramref name="degrees"/> (right ear down) about the line along <paramref name="aim"/> through <paramref name="eye"/>. </summary>
	public bool Apply( SkinnedModelRenderer body, Vector3 eye, Vector3 aim, float degrees )
	{
		if ( MathF.Abs( degrees ) < .01f || aim.IsNearZeroLength || !body.IsValid() || !body.SceneModel.IsValid() || body.Model is null ) return false;
		if ( _model != body.Model || _body != body ) Build( body );
		if ( _head < 0 || _neck < 0 ) return false;

		var scene = body.SceneModel;
		// Read before writing: the engine may propagate a parent change to its children.
		for ( var i = 0; i < _bones.Length; i++ ) _pose[i] = scene.GetBoneWorldTransform( _bones[i] );
		var neck = scene.GetBoneWorldTransform( _neck ).Position;
		var head = scene.GetBoneWorldTransform( _head ).Position;
		// About the forward axis a positive turn takes left up, so the right ear goes down.
		var roll = Rotation.FromAxis( aim.Normal, degrees );
		var swing = Rotation.FromToRotation( head - neck, eye + roll * (head - eye) - neck );
		for ( var i = 0; i < _bones.Length; i++ )
		{
			var pose = _pose[i];
			_pose[i] = _inHead[i]
				? pose.WithPosition( eye + roll * (pose.Position - eye) ).WithRotation( roll * pose.Rotation )
				: pose.WithPosition( neck + swing * (pose.Position - neck) ).WithRotation( swing * pose.Rotation );
		}
		for ( var i = 0; i < _bones.Length; i++ ) scene.SetBoneWorldTransform( _bones[i], _pose[i] );

		// The helmet and anything else merged onto the head must follow it.
		foreach ( var garment in _garments )
		{
			if ( garment.IsValid() && garment.Enabled && garment.BoneMergeTarget == body && garment.SceneModel.IsValid() )
				garment.SceneModel.MergeBones( scene );
		}
		return true;
	}

	private void Build( SkinnedModelRenderer body )
	{
		_body = body;
		_model = body.Model;
		var bones = _model.Bones;
		_neck = (bones.GetBone( "neck_0" ) ?? bones.GetBone( "neck" ))?.Index ?? -1;
		_head = bones.GetBone( "head" )?.Index ?? -1;
		if ( _neck < 0 || _head < 0 || !Under( _head, _neck ) ) { _head = -1; return; }
		_bones = bones.AllBones.Where( b => Under( b.Index, _neck ) ).OrderBy( b => Depth( b.Index ) ).Select( b => b.Index ).ToArray();
		_inHead = _bones.Select( i => Under( i, _head ) ).ToArray();
		_pose = new Transform[_bones.Length];
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
