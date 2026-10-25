"""Offline checks only: HLSL core syntax and foam opacity/placement."""
from pathlib import Path
import ctypes as C,json,hashlib,re,sys,py_compile
import numpy as np
from PIL import Image
r=Path('C:/Users/mimi-/Documents/S&box Projects/hc1');out=Path(__file__).parent
shader=r/'Assets/shaders/forestbase_current.shader';text=shader.read_text()
core=text[text.index('    float CurrentHash'):].rsplit('}',1)[0]
core=core.replace('Material::From(i)','GetMaterial(i)').replace('ShadingModelStandard::Shade(i,m)','float4(m.Albedo,m.Opacity)')
stub='''Texture2D<float4> CurrentTexture; SamplerState CurrentSampler; float g_flTime;
struct PixelInput { float2 vTextureCoords:TEXCOORD0; float3 position:TEXCOORD1; };
struct Material { float3 WorldPosition; float3 Albedo; float Roughness; float Metalness; float AmbientOcclusion; float Opacity; };
Material GetMaterial(PixelInput i) { Material m=(Material)0;m.WorldPosition=i.position;return m; }
'''+core
(out/'core-check.hlsl').write_text(stub)
compile=C.WinDLL('d3dcompiler_47.dll').D3DCompile
compile.argtypes=[C.c_void_p,C.c_size_t,C.c_char_p,C.c_void_p,C.c_void_p,C.c_char_p,C.c_char_p,C.c_uint,C.c_uint,C.POINTER(C.c_void_p),C.POINTER(C.c_void_p)]
compile.restype=C.c_long
code=C.c_void_p();errors=C.c_void_p();data=stub.encode()
result=compile(data,len(data),b'core-check.hlsl',None,None,b'MainPs',b'ps_5_0',1<<11,0,C.byref(code),C.byref(errors))
def blob(pointer):
    vt=C.cast(pointer,C.POINTER(C.POINTER(C.c_void_p))).contents
    address=C.WINFUNCTYPE(C.c_void_p,C.c_void_p)(vt[3])(pointer)
    size=C.WINFUNCTYPE(C.c_size_t,C.c_void_p)(vt[4])(pointer)
    return C.string_at(address,size)
diagnostics=blob(errors).decode(errors='replace') if errors else ''
(out/'core-check.log').write_text(diagnostics or 'HLSL core compiled successfully with Direct3D compiler; engine wrappers are stubbed.\n')
assert result>=0,diagnostics
for pointer in (code,errors):
    if pointer:
        vt=C.cast(pointer,C.POINTER(C.POINTER(C.c_void_p))).contents;C.WINFUNCTYPE(C.c_ulong,C.c_void_p)(vt[2])(pointer)
py_compile.compile(str(r/'Tools/forestbase_water.py'),doraise=True)
mask=np.asarray(Image.open(r/'Assets/materials/forestbase/waterfall_current_mask.png'),float)/255
def smooth(a,b,v):
    q=np.clip((v-a)/(b-a),0,1);return q*q*(3-2*q)
def sample(uv):
    h,w=mask.shape;xy=uv*np.array((w,h))-.5;k=np.floor(xy).astype(int);f=xy-k;x,y=k[...,0],k[...,1]
    a=mask[y%h,x%w]*(1-f[...,0])+mask[y%h,(x+1)%w]*f[...,0]
    b=mask[(y+1)%h,x%w]*(1-f[...,0])+mask[(y+1)%h,(x+1)%w]*f[...,0]
    return a*(1-f[...,1])+b*f[...,1]
def hash(p):
    q=np.sin(p[...,0]*127.1+p[...,1]*311.7)*43758.5453;return q-np.floor(q)
def noise(p):
    a=np.floor(p);f=p-a;f=f*f*(3-2*f)
    return (hash(a)*(1-f[...,0])+hash(a+(1,0))*f[...,0])*(1-f[...,1])+(hash(a+(0,1))*(1-f[...,0])+hash(a+(1,1))*f[...,0])*f[...,1]
v,u=np.mgrid[0:1:129j,0:1:97j];uv=np.stack((u,v),-1)
edge=smooth(0,.18,u)*smooth(0,.18,1-u)*smooth(0,.22,v)*smooth(0,.22,1-v)
peaks=[];means=[];patches=[]
for k in range(10):
    t=(k+.6)/10;e=np.sin(t*7)*35+np.sin(k*2.1)*110;n=-1450-t*1650
    p=np.stack((n-145+v*290,-(e-100+u*200)),-1)
    for time in (0,.25,1,3):
        flow=p+(time*18,0);warp=np.stack((noise(flow*.004),noise(flow*.004+17.3)),-1)-.5;q=flow*.0025+warp*.35
        rotated=np.stack((q[...,0]*.8-q[...,1]*.6,q[...,0]*.6+q[...,1]*.8),-1)
        a=sample(rotated+(.23,.61));b=sample(np.stack((-q[...,1],q[...,0]),-1)*1.37+(.71,.13))
        alpha=np.clip(a*.55+b*.45,0,1)*edge*smooth(.25,.75,noise(flow*.006+41.7))*.14
        assert np.isfinite(alpha).all() and alpha.max()<=.14
        assert not alpha[0].any() and not alpha[-1].any() and not alpha[:,0].any() and not alpha[:,-1].any()
        peaks.append(float(alpha.max()));means.append(float(alpha.mean()))
        if time==0:patches.append(alpha)
assert all(not np.array_equal(patches[0],p) for p in patches[1:])
old=r/'Assets/shaders/forestbase_foam.shader'
assert 'clip(' not in text and 'Froth' not in text
assert 'forestbase_current.shader' in (r/'Assets/materials/forestbase/waterfall_current.vmat').read_text()
protected=[r/'Assets/shaders'/n for n in ('forestbase_foam.shader','forestbase_river.shader','forestbase_basin.shader','forestbase_waterfall.shader')]
protected+=[r/'Assets/models/maps/forestbase'/n for n in ('vista.obj','vista.vmdl','motor.obj','yard.obj')]
report={'editorUsed':False,'engineCompileVerified':False,'hlslCoreCompilation':'passed with engine-only wrappers stubbed',
        'alphaUpperBound':.14,'observedMaximumAlpha':max(peaks),'observedMeanAlphaRange':[min(means),max(means)],
        'patchesChecked':10,'timeSamplesPerPatch':4,'allPatchEdgesZeroAlpha':True,'patchPatternsDistinct':True,
        'newTextureSources':0,'meshAndCollisionChanges':False,
        'installed':{str(p.relative_to(r)):hashlib.sha256(p.read_bytes()).hexdigest() for p in (shader,r/'Assets/materials/forestbase/waterfall_current.vmat',r/'Tools/forestbase_water.py')},
        'protectedSourceHashes':{str(p.relative_to(r)):hashlib.sha256(p.read_bytes()).hexdigest() for p in protected}}
(out/'integration.json').write_text(json.dumps(report,indent=2));print(json.dumps({k:v for k,v in report.items() if not k.endswith('Hashes') and k!='installed'},indent=2))
