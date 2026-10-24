"""Create the v3 surface shader from the verified clear-water implementation."""
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
source=ROOT/'Sources/Belltower/shaders/belltower_fountain_surface_v2.shader'
target=source.with_name('belltower_fountain_surface_v3.shader')
text=source.read_text()
start=text.index('    float3 Impact(')
end=text.index('    float4 MainPs(',start)
impact='''    float FountainHash21(float2 p)
    {
        return frac(sin(dot(p,float2(127.1,311.7)))*43758.5453);
    }
    float FountainNoise(float2 p)
    {
        float2 cell=floor(p);
        float2 f=frac(p); f=f*f*(3-2*f);
        return lerp(lerp(FountainHash21(cell),FountainHash21(cell+float2(1,0)),f.x),
                    lerp(FountainHash21(cell+float2(0,1)),FountainHash21(cell+1),f.x),f.y);
    }
    float3 Impact(float2 delta,float phase)
    {
        float2 drift=.14*float2(sin(g_flTime*4.3+phase),cos(g_flTime*3.7+phase));
        float2 p=delta+drift;
        float radius=length(p);
        float angle=atan2(p.y,p.x);
        float envelope=exp(-radius/10)*smoothstep(.6,2.0,radius);
        float waviness=.15*sin(angle*3+phase)+.07*sin(angle*7-g_flTime*.8);
        float wave=radius*1.85-g_flTime*9.2+phase+waviness;
        float resolved=1-smoothstep(.55,1.6,fwidth(radius)*1.85);
        float2 slope=p/max(radius,.08)*(cos(wave)+.28*cos(wave*1.71+phase))*envelope*.10*resolved;
        float boil=exp(-radius*radius/7.0);
        slope+=float2(FountainNoise(p*2.5+float2(g_flTime*1.4,phase))-.5,
                      FountainNoise(p*2.9+float2(phase,-g_flTime*1.7))-.5)*boil*.42;
        // Sparse, short-lived millimetre-scale bubble rims replace the former
        // solid radial foam disc. Derivatives suppress distant pixel sparkle.
        float2 bubbleUv=p*2.1+float2(g_flTime*.12,phase);
        float2 cell=floor(bubbleUv);
        float seed=FountainHash21(cell+phase);
        float2 centre=.25+.5*float2(seed,FountainHash21(cell+17));
        float d=length(frac(bubbleUv)-centre);
        float r=lerp(.12,.25,FountainHash21(cell+41));
        float aa=max(.025,length(fwidth(bubbleUv))*.7);
        float ring=1-smoothstep(.025,.025+aa,abs(d-r));
        float life=frac(seed+g_flTime*1.1);
        float alive=smoothstep(0,.1,life)*(1-smoothstep(.35,.72,life));
        float bubbles=boil*ring*alive*step(.48,seed)*.32;
        return float3(slope,bubbles);
    }
'''
text=text[:start]+impact+text[end:]
text=text.replace('Belltower clear shallow fountain water and fading impact ripples',
                  'Belltower clear shallow water with capillary ripples and fine aerated impacts')
assert not target.exists(), 'Keep existing shader source revisions.'
target.write_text(text)
print(target)
