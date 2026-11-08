import map_kit as K
MODEL='models/maps/belltower/well-frame-v2/well_frame.vmdl'
def group(ids):
    key='well_frame'
    child=K.game_object(ids,'Garden well frame',key,K.to_world((0,-1225,-48)),components=[K.component(ids,'Sandbox.ModelRenderer',key+'/renderer',Model=MODEL,RenderType='On',Tint='1,1,1,1')])
    return K.game_object(ids,'Garden well frame',key+'/group',children=[child])
