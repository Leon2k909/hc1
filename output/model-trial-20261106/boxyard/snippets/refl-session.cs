
var f = System.Reflection.BindingFlags.Instance | System.Reflection.BindingFlags.Public | System.Reflection.BindingFlags.NonPublic | System.Reflection.BindingFlags.Static;
var t = typeof( Editor.SceneEditorSession );
var mem = t.GetMembers( f ).Where( m => { var n = m.Name; return n.Contains( "Camera" ) || n.Contains( "View" ) || n.Contains( "Frame" ) || n.Contains( "Look" ); } )
    .Select( m => m.MemberType + " " + m.Name + ( m is System.Reflection.MethodBase mb ? "(" + string.Join( ",", mb.GetParameters().Select( p => p.ParameterType.Name + " " + p.Name ) ) + ")" : m is System.Reflection.PropertyInfo pi ? ":" + pi.PropertyType.Name : m is System.Reflection.FieldInfo fi ? ":" + fi.FieldType.Name : "" ) ).Distinct().ToList();
var types = typeof( Editor.SceneEditorSession ).Assembly.GetTypes().Where( x => x.Name.Contains( "SceneView" ) || x.Name.Contains( "ViewportCamera" ) || x.Name.Contains( "EditorCamera" ) || x.Name.Contains( "CameraState" ) ).Select( x => x.FullName ).ToList();
return new { mem, types };
