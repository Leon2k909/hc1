"""Blender node approximation of forestbase_rock.shader's weathering formulas.

Uses world coordinates in engine inches and the same polynomial noise formula.
Numerical precision, lights, tangent normals and native PBR shading can differ.
"""
import bpy
import re


def node_math(nodes,links,operation,*values):
    node=nodes.new('ShaderNodeMath');node.operation=operation
    for socket,value in zip(node.inputs,values):
        if isinstance(value,(int,float)):socket.default_value=value
        else:links.new(value,socket)
    return node.outputs[0]


def group(name,inputs):
    if name in bpy.data.node_groups:return bpy.data.node_groups[name]
    tree=bpy.data.node_groups.new(name,'ShaderNodeTree')
    for key in inputs:tree.interface.new_socket(name=key,in_out='INPUT',socket_type='NodeSocketFloat')
    tree.interface.new_socket(name='Value',in_out='OUTPUT',socket_type='NodeSocketFloat')
    return tree


def noise_groups():
    name='Forest rock polynomial hash'
    if name not in bpy.data.node_groups:
        tree=group(name,('X','Y'));nodes,links=tree.nodes,tree.links
        i=nodes.new('NodeGroupInput');o=nodes.new('NodeGroupOutput')
        op=lambda kind,*args:node_math(nodes,links,kind,*args)
        x=op('FRACT',op('MULTIPLY',i.outputs['X'],.1031))
        y=op('FRACT',op('MULTIPLY',i.outputs['Y'],.1031))
        z=x
        d=op('ADD',op('ADD',op('MULTIPLY',x,op('ADD',y,33.33)),
                            op('MULTIPLY',y,op('ADD',z,33.33))),op('MULTIPLY',z,op('ADD',x,33.33)))
        result=op('FRACT',op('MULTIPLY',op('ADD',op('ADD',x,d),op('ADD',y,d)),op('ADD',z,d)))
        links.new(result,o.inputs['Value'])
    hash_tree=bpy.data.node_groups[name]
    name='Forest rock smooth noise'
    if name not in bpy.data.node_groups:
        tree=group(name,('X','Y'));nodes,links=tree.nodes,tree.links
        i=nodes.new('NodeGroupInput');o=nodes.new('NodeGroupOutput')
        op=lambda kind,*args:node_math(nodes,links,kind,*args)
        def lerp(a,b,t):return op('ADD',op('MULTIPLY',a,op('SUBTRACT',1,t)),op('MULTIPLY',b,t))
        x,y=op('FLOOR',i.outputs['X']),op('FLOOR',i.outputs['Y'])
        fx,fy=op('FRACT',i.outputs['X']),op('FRACT',i.outputs['Y'])
        fx=op('MULTIPLY',op('MULTIPLY',fx,fx),op('SUBTRACT',3,op('MULTIPLY',2,fx)))
        fy=op('MULTIPLY',op('MULTIPLY',fy,fy),op('SUBTRACT',3,op('MULTIPLY',2,fy)))
        def sample(dx,dy):
            node=nodes.new('ShaderNodeGroup');node.node_tree=hash_tree
            links.new(op('ADD',x,dx),node.inputs['X']);links.new(op('ADD',y,dy),node.inputs['Y'])
            return node.outputs[0]
        result=lerp(lerp(sample(0,0),sample(1,0),fx),lerp(sample(0,1),sample(1,1),fx),fy)
        links.new(result,o.inputs['Value'])
    return bpy.data.node_groups[name]


def apply(mat,bsdf,color,text):
    nodes,links=mat.node_tree.nodes,mat.node_tree.links
    op=lambda kind,*args:node_math(nodes,links,kind,*args)
    def scalar(key,default):
        m=re.search(r'\b'+key+r'\s+"([\d.]+)"',text)
        return float(m[1]) if m else default
    def vector(key,default):
        m=re.search(r'\b'+key+r'\s+"\[([^]]+)\]"',text)
        return tuple(map(float,m[1].split())) if m else default
    def clamp(v):return op('MINIMUM',1,op('MAXIMUM',0,v))
    def smooth(a,b,v):
        t=clamp(op('DIVIDE',op('SUBTRACT',v,a),b-a))
        return op('MULTIPLY',op('MULTIPLY',t,t),op('SUBTRACT',3,op('MULTIPLY',2,t)))
    def lerp(a,b,t):return op('ADD',op('MULTIPLY',a,op('SUBTRACT',1,t)),op('MULTIPLY',b,t))
    def rgb(a,b,factor,mode='MIX'):
        node=nodes.new('ShaderNodeMixRGB');node.blend_type=mode
        for socket,value in zip(node.inputs,(factor,a,b)):
            if isinstance(value,tuple):socket.default_value=(*value,1)
            elif isinstance(value,(int,float)):socket.default_value=value
            else:links.new(value,socket)
        return node.outputs[0]
    def vscale(v,s):
        node=nodes.new('ShaderNodeVectorMath');node.operation='SCALE'
        links.new(v,node.inputs[0]);links.new(s,node.inputs[3]);return node.outputs[0]
    def vadd(a,b):
        node=nodes.new('ShaderNodeVectorMath');node.operation='ADD'
        links.new(a,node.inputs[0]);links.new(b,node.inputs[1]);return node.outputs[0]
    geom=nodes.new('ShaderNodeNewGeometry')
    scale=nodes.new('ShaderNodeVectorMath');scale.operation='SCALE';scale.inputs[3].default_value=1/.0254
    links.new(geom.outputs['Position'],scale.inputs[0])
    separate=nodes.new('ShaderNodeSeparateXYZ');links.new(scale.outputs[0],separate.inputs[0])
    x,y,z=(separate.outputs[k] for k in ('X','Y','Z'))
    def noise(a,b):
        node=nodes.new('ShaderNodeGroup');node.node_tree=noise_groups()
        links.new(a,node.inputs['X']);links.new(b,node.inputs['Y']);return node.outputs[0]
    coarse=noise(op('ADD',op('MULTIPLY',x,.0075),op('MULTIPLY',z,.002)),
                 op('ADD',op('MULTIPLY',y,.0075),op('MULTIPLY',z,.002)))
    streak=noise(op('ADD',op('MULTIPLY',x,.024),op('MULTIPLY',y,.011)),op('MULTIPLY',z,.002))
    ns=nodes.new('ShaderNodeSeparateXYZ');links.new(geom.outputs['Normal'],ns.inputs[0])
    up=clamp(ns.outputs['Z'])
    rough=bsdf.inputs['Roughness'].links[0].from_socket if bsdf.inputs['Roughness'].is_linked else bsdf.inputs['Roughness'].default_value
    cover=op('ADD',op('ADD',op('MULTIPLY',.65,coarse),op('MULTIPLY',.35,streak)),op('MULTIPLY',.15,op('SUBTRACT',1,rough)))
    moss=op('MULTIPLY',scalar('MossAmount',.8),op('MULTIPLY',smooth(.22,.78,up),smooth(.30,.68,cover)))
    wet=clamp(op('ADD',op('ADD',scalar('RockWetness',.55),op('MULTIPLY',.24,op('SUBTRACT',streak,.5))),
                 op('MULTIPLY',.30,op('SUBTRACT',1,smooth(-285,-155,z)))))
    sep=nodes.new('ShaderNodeSeparateColor');sep.mode='RGB';links.new(color,sep.inputs[0])
    lum=op('ADD',op('ADD',op('MULTIPLY',sep.outputs[0],.2126),op('MULTIPLY',sep.outputs[1],.7152)),op('MULTIPLY',sep.outputs[2],.0722))
    neutral=nodes.new('ShaderNodeCombineColor');neutral.mode='RGB'
    for socket in list(neutral.inputs)[:3]:links.new(lum,socket)
    stone=rgb(color,neutral.outputs[0],scalar('RockDesaturation',.82))
    stone=rgb(stone,vector('RockTint',(.78,.84,.86)),1,'MULTIPLY')
    stone=rgb(stone,lerp(1,.62,wet),1,'MULTIPLY')
    mosscolor=rgb(vector('MossTint',(.035,.065,.025)),op('ADD',.55,op('MULTIPLY',1.5,lum)),1,'MULTIPLY')
    links.new(rgb(stone,mosscolor,moss),bsdf.inputs['Base Color'])
    rough=lerp(op('MAXIMUM',.48,rough),.25,op('MULTIPLY',wet,.7))
    links.new(lerp(rough,lerp(.9,.75,wet),moss),bsdf.inputs['Roughness'])
    if bsdf.inputs['Normal'].is_linked:
        old=bsdf.inputs['Normal'].links[0].from_socket
        amount=op('MULTIPLY',.12,op('MULTIPLY',wet,op('SUBTRACT',1,moss)))
        mixed=vadd(vscale(old,op('SUBTRACT',1,amount)),vscale(geom.outputs['Normal'],amount))
        unit=nodes.new('ShaderNodeVectorMath');unit.operation='NORMALIZE';links.new(mixed,unit.inputs[0])
        links.new(unit.outputs[0],bsdf.inputs['Normal'])
