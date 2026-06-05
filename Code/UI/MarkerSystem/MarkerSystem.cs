namespace Facepunch.UI;

public partial class MarkerSystem : Panel
{
	private const float RefreshInterval = 0.1f;
	private readonly List<IMarkerObject> _deleteList = new();
	private TimeSince _timeSinceRefresh;

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

	public override void Tick()
	{
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
