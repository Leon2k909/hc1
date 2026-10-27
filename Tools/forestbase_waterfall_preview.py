"""Static t=0 Blender approximation of the saved native waterfall formulas.

UV progress follows the exported OBJ. Native derivative-based importer-flip
recovery, animation, fog, sampling/compression and shading still need the engine.
"""
import bpy
import re
from forestbase_rock_preview import node_math


def apply(mat,text,assets):
    nodes,links=mat.node_tree.nodes,mat.node_tree.links;nodes.clear()
    output=nodes.new('ShaderNodeOutputMaterial');bsdf=nodes.new('ShaderNodeBsdfPrincipled')
    links.new(bsdf.outputs[0],output.inputs['Surface'])
    bsdf.inputs['Metallic'].default_value=0;bsdf.inputs['Emission Strength'].default_value=1
    op=lambda kind,*values:node_math(nodes,links,kind,*values)
    def clamp(v):return op('MINIMUM',1,op('MAXIMUM',0,v))
    def smooth(a,b,v):
        t=clamp(op('DIVIDE',op('SUBTRACT',v,a),b-a))
        return op('MULTIPLY',op('MULTIPLY',t,t),op('SUBTRACT',3,op('MULTIPLY',2,t)))
    def lerp(a,b,t):return op('ADD',op('MULTIPLY',a,op('SUBTRACT',1,t)),op('MULTIPLY',b,t))
    def rgb(a,b,t):
        n=nodes.new('ShaderNodeMixRGB');links.new(t,n.inputs[0])
        n.inputs[1].default_value=(*a,1);n.inputs[2].default_value=(*b,1);return n.outputs[0]
    uv=nodes.new('ShaderNodeTexCoord');sep=nodes.new('ShaderNodeSeparateXYZ');links.new(uv.outputs['UV'],sep.inputs[0])
    u,v=sep.outputs['X'],sep.outputs['Y']
    m=re.search(r'\bFlowTiling\s+"([\d.]+)"',text);tiling=float(m[1]) if m else 4
    m=re.search(r'\bFlowMask\s+"([^\"]+)"',text)
    path=assets/(m[1] if m else 'materials/forestbase/waterfall_froth_v2.png')
    image=bpy.data.images.load(str(path),check_existing=True);image.colorspace_settings.name='Non-Color'
    def sample(x,y):
        tex=nodes.new('ShaderNodeTexImage');tex.image=image;tex.extension='REPEAT'
        vec=nodes.new('ShaderNodeCombineXYZ');links.new(x,vec.inputs[0]);links.new(y,vec.inputs[1]);links.new(vec.outputs[0],tex.inputs[0])
        split=nodes.new('ShaderNodeSeparateColor');split.mode='RGB';links.new(tex.outputs['Color'],split.inputs[0])
        return split.outputs[0],split.outputs[1]
    phase=op('MULTIPLY',op('SQRT',op('MAXIMUM',v,.005)),2.6)
    flow=op('MULTIPLY',u,tiling)
    drift=op('MULTIPLY',op('SINE',op('MULTIPLY',v,11)),.012)
    coarse,cg=sample(op('MULTIPLY',flow,.27),op('MULTIPLY',phase,.48))
    bend=op('ADD',op('MULTIPLY',op('SUBTRACT',cg,.5),.12),drift)
    a,ag=sample(op('ADD',op('MULTIPLY',flow,.85),bend),phase)
    b,bg=sample(op('SUBTRACT',op('MULTIPLY',flow,2.4),bend),op('MULTIPLY',phase,1.21))
    density=op('MULTIPLY',lerp(a,b,.24),lerp(.70,1.17,coarse))
    foam=clamp(op('MULTIPLY',smooth(.16,.80,density),op('ADD',.65,op('MULTIPLY',.30,v))))
    fray=op('ADD',op('MULTIPLY',.014,op('SINE',op('MULTIPLY',v,19))),op('MULTIPLY',.012,op('SUBTRACT',coarse,.5)))
    edge=op('MULTIPLY',smooth(0,.04,op('SUBTRACT',op('ADD',u,drift),fray)),
            smooth(0,.04,op('SUBTRACT',op('SUBTRACT',op('SUBTRACT',1,u),drift),fray)))
    geometry=nodes.new('ShaderNodeNewGeometry');xyz=nodes.new('ShaderNodeSeparateXYZ');links.new(geometry.outputs['Position'],xyz.inputs[0])
    z=op('DIVIDE',xyz.outputs['Z'],.0254)
    tail=smooth(-255,-110,z);entry=smooth(0,.02,v);strands=smooth(.24,.76,density)
    alpha=op('MULTIPLY',op('MULTIPLY',op('MULTIPLY',edge,tail),entry),
             op('ADD',.18,op('MULTIPLY',strands,op('ADD',.48,op('MULTIPLY',.30,v)))))
    alpha=op('MULTIPLY',alpha,op('GREATER_THAN',alpha,.025))
    links.new(alpha,bsdf.inputs['Alpha'])
    links.new(rgb((.025,.04,.055),(.22,.27,.30),foam),bsdf.inputs['Base Color'])
    links.new(rgb((.035,.055,.065),(.28,.33,.36),foam),bsdf.inputs['Emission Color'])
    links.new(lerp(.28,.90,foam),bsdf.inputs['Roughness'])
