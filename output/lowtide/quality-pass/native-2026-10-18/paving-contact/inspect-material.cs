var material=Material.Load("materials/lowtide/paving-use/lt_setts_review.vmat");
if(material.IsError || material.Shader==null || !material.ShaderName.Contains("hc1_lowtide_paving_use"))throw new Exception("Candidate shader failed");
var use=material.GetTexture("g_tPavingUse");
if(use?.Width!=2048 || use.Height!=2048)throw new Exception("Contact mask missing");
var report=new{material.ShaderName,material.IsError,TextureWidth=use.Width,TextureHeight=use.Height,Strength=material.GetVector4("g_flPavingUse"),TimeUtc=DateTime.UtcNow};
System.IO.File.WriteAllText(System.IO.Path.Combine(Project.Current.GetRootPath(),"output/lowtide/quality-pass/native-2026-10-18/paving-contact/material-readback.json"),System.Text.Json.JsonSerializer.Serialize(report,new System.Text.Json.JsonSerializerOptions{WriteIndented=true}));
return report;
