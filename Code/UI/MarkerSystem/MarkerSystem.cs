namespace Facepunch.UI;

public partial class MarkerSystem : Panel
{
	private const float RefreshInterval = 0.1f;
	private readonly List<IMarkerObject> _deleteList = new();
	private TimeSince _timeSinceRefresh;
	private ViewModelMask _gunMask;
	private Texture _maskImage;

	public Dictionary<IMarkerObject, Marker> ActiveMarkers { get; set; } = new();

	void Refresh()
	{
		if ( Scene is null ) return;

		_deleteList.Clear();
		_deleteList.AddRange( ActiveMarkers.Keys );

		foreach ( var markerObject in Scene.GetAllComponents<IMarkerObject>() )
		{
			if ( UpdateMarker( markerObject ) )
			{
				_deleteList.Remove( markerObject );
			}
		}

		foreach ( var marker in _deleteList )
		{
			ActiveMarkers[marker].Delete();
			ActiveMarkers.Remove( marker );
		}
	}

	public Marker CreateMarker( IMarkerObject marker )
	{
		var inst = new Marker()
		{
			Object = marker,
		};
		AddChild( inst );
		return inst;
	}

	public bool UpdateMarker( IMarkerObject marker )
	{
		if ( !marker.GameObject.IsValid() )
			return false;

		if ( !marker.ShouldShow() )
			return false;

		var camera = Scene.Camera;
		if ( !camera.IsValid() )
			return false;

		if ( marker.MarkerMaxDistance != 0f && camera.WorldPosition.DistanceSquared( marker.MarkerPosition ) > marker.MarkerMaxDistance * marker.MarkerMaxDistance )
			return false;

		if ( !ActiveMarkers.TryGetValue( marker, out var instance ) )
		{
			instance = CreateMarker( marker );
			if ( instance.IsValid() )
			{
				ActiveMarkers[marker] = instance;
			}
		}

		instance.Reposition();

		return true;
	}

	/// <summary>
	/// The first-person gun draws over the markers: they're masked out wherever it covers the view.
	/// </summary>
	void UpdateGunMask()
	{
		// Made here, not in an initialiser: a hotload leaves a new field on an existing panel null.
		_gunMask ??= new ViewModelMask();

		// Only while there are markers to hide, since the mask draws the viewmodel a second time.
		_gunMask.Update( ActiveMarkers.Count > 0 ? Scene : null );

		var texture = _gunMask.Texture;
		if ( texture == _maskImage )
			return;

		_maskImage = texture;
		Style.MaskImage = texture;

		if ( texture is null )
			return;

		Style.MaskMode = MaskMode.Luminance;
		Style.MaskSizeX = Length.Percent( 100 );
		Style.MaskSizeY = Length.Percent( 100 );
		Style.MaskRepeat = BackgroundRepeat.Clamp;
	}

	public override void OnDeleted()
	{
		base.OnDeleted();

		_gunMask?.Dispose();
	}

	public override void Tick()
	{
		UpdateGunMask();

		foreach ( var pair in ActiveMarkers )
		{
			if ( pair.Value.IsValid() )
			{
				pair.Value.Reposition();
			}
		}

		if ( _timeSinceRefresh < RefreshInterval )
			return;

		_timeSinceRefresh = 0f;
		Refresh();
	}
}
