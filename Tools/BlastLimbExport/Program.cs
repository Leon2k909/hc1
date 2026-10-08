using ValveResourceFormat;
using ValveResourceFormat.ResourceTypes;
using ValveResourceFormat.IO;

using var resource = new Resource();
resource.Read( args[0] );
var model = (Model)resource.DataBlock;
// s&box uses a packed normal stream the glTF exporter does not support. The
// generator reconstructs smooth normals from the exported geometry instead.
foreach ( var mesh in model.GetEmbeddedMeshes() )
{
	var buffers = mesh.Mesh.VBIB.VertexBuffers;
	for ( var i = 0; i < buffers.Count; ++i )
	{
		var buffer = buffers[i];
		buffer.InputLayoutFields = buffer.InputLayoutFields.Where( a => a.SemanticName != "NORMAL" ).ToArray();
		buffers[i] = buffer;
	}
}
var exporter = new GltfModelExporter( new NullFileLoader() )
{
	ExportMaterials = false, ExportAnimations = true, ProgressReporter = new Progress<string>( Console.WriteLine )
};
exporter.Export( resource, args[1] );
