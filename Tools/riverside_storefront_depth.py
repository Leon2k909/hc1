"""Approved real shop glazing; geometry uses baked map coordinates."""
import map_kit as K

def scene_object():
    ids=K.SceneIds('f1544f30-4a18-4875-a27b-24803592d2f3');key='store/glazed-windows'
    return K.game_object(ids,'Lucky Stop Glazed Windows',key,components=[K.component(ids,'Sandbox.ModelRenderer',key+'/renderer',Model='models/props/riverside/storefront_depth_v1/windows.vmdl',BodyGroups=18446744073709551615,RenderType='On',Tint='1,1,1,1')])
