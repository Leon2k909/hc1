from pathlib import Path
import json,subprocess,shutil
r=Path('C:/Users/mimi-/Documents/S&box Projects/hc1');out=Path(__file__).parent
before=(out/'forestbase_waterfall.shader.before').read_text()
head=before[:before.index('    float4 MainPs')]
head=head.replace('sin(h*.035+g_flTime*3.2+u*23)*3.5','sin(h*.035+g_flTime*3.2+u*23)*2.4').replace('sin(h*.081+g_flTime*6.6-u*49)*1.7','sin(h*.081+g_flTime*6.6-u*49)*1.1')
body='''    float4 MainPs(PixelInput i) : SV_Target0
    {
        Material m=Material::From(i);
        float2 uvDx=ddx(i.vTextureCoords.xy),uvDy=ddy(i.vTextureCoords.xy);
        float uvDet=uvDx.x*uvDy.y-uvDx.y*uvDy.x;
        float heightAlongV=uvDx.x*ddy(m.WorldPosition.z)-uvDy.x*ddx(m.WorldPosition.z);
        float progress=saturate(heightAlongV*uvDet<0?i.vTextureCoords.y:1-i.vTextureCoords.y);
        float2 uv=float2(i.vTextureCoords.x,progress);
        float flowX=uv.x*FlowTiling;
        float phase=sqrt(max(progress,.005))*5.8-g_flTime*1.32+FlowPhase;
        float3 coarse=FlowTexture.Sample(FlowSampler,float2(flowX*.48,phase*.27)).rgb;
        float bend=(coarse.g-.5)*.13+sin(progress*11+g_flTime*.35)*.015;
        float3 a=FlowTexture.Sample(FlowSampler,float2(flowX*1.45+bend,phase)).rgb;
        float3 b=FlowTexture.Sample(FlowSampler,float2(flowX*3.8-bend,phase*1.19-g_flTime*.16)).rgb;
        float density=saturate(a.r*.63+b.r*.37);
        // One broad falling body, with a dense centre and irregular soft edges.
        // The previous three Gaussian channels exposed large strips of rock.
        float centre=.5+.018*sin(progress*10)+.012*sin(progress*23+1.7);
        float width=lerp(.23,.32,pow(progress,.7));
        float fray=(coarse.r-.5)*.045+(a.g-.5)*.018;
        float distanceFromCentre=abs((uv.x-centre+fray)/width);
        float curtain=1-smoothstep(.72,1.12,distanceFromCentre);
        float core=1-smoothstep(.28,.82,distanceFromCentre);
        float filaments=smoothstep(.18,.72,density);
        float aeration=saturate(.42+filaments*.40+core*.18+progress*.10);
        float tail=smoothstep(-260,-150,m.WorldPosition.z);
        float entry=smoothstep(0,.018,progress);
        float3 tangent=normalize(i.vTangentUWs);
        float3 along=normalize(i.vTangentVWs);
        m.Normal=normalize(m.Normal+tangent*(a.g-b.g)*.20+along*(coarse.b-.5)*.10);
        m.Albedo=lerp(float3(.24,.34,.36),float3(.72,.79,.80),aeration);
        m.Emission=float3(.16,.19,.20)*aeration;
        m.Roughness=lerp(.48,.88,aeration);
        m.Metalness=0;
        m.AmbientOcclusion=1;
        // Keep a continuous translucent water body; detail varies density
        // instead of cutting the fall into see-through threads.
        m.Opacity=curtain*tail*entry*(.70+.27*filaments);
        return ShadingModelStandard::Shade(i,m);
    }
}
'''
(out/'forestbase_waterfall.next.shader').write_text(head+body)
basin=(out/'forestbase_basin.shader.before').read_text()
basin=basin.replace('float3(.019,.038,.041),float3(.032,.059,.060)','float3(.020,.068,.078),float3(.032,.102,.111)')
basin=basin.replace('lerp(.085+churn*.065,.51,foam)','lerp(.16+churn*.065,.55,foam)')
(out/'forestbase_basin.next.shader').write_text(basin)
for name,strength in [('waterfall_impact',3.2),('waterfall_spray',1.8)]:
    p=r/'Assets/materials/forestbase'/(name+'.vmat');shutil.copy2(p,out/(name+'.before.vmat'))
    s=p.read_text()
    import re
    if 'MistStrength' in s:s=re.sub(r'MistStrength "[^\"]+"',f'MistStrength "{strength}"',s)
    else:s=s.replace(' ConstrainPlungeBasin',f' MistStrength "{strength}"\n ConstrainPlungeBasin')
    (out/(name+'.next.vmat')).write_text(s)
print('Staged two shaders and two mist materials; existing water/rock geometry retained.')
