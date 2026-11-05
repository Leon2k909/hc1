var session = Editor.SceneEditorSession.All.Single(x => x.Scene.Name == "sewage");
return new { Methods = session.GetType().GetMethods().Where(x => x.Name.Contains("Save")).Select(x=>x.ToString()).ToArray(), Properties=session.GetType().GetProperties().Where(x=>x.Name.Contains("File") || x.Name.Contains("Unsaved")).Select(x=>new {x.Name,Type=x.PropertyType.FullName}).ToArray() };
