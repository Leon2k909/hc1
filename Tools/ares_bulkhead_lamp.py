"""Approved lower-hall bulkhead fixture; original embedded lamp is removed."""
import map_kit as K
MODEL='models/props/ares/bulkhead_lamp_native_v1/lamp.vmdl'
def is_replaced(e,n,z,facing):
    return abs(e+1100)<.01 and abs(n+300)<.01 and abs(z-120)<.01 and tuple(facing)==(1,0)
def scene_object(ids):
    return K.game_object(ids,'Lower Hall Bulkhead Lamp','hall/bulkhead-lamp-native-v1',(-300,1100,120),components=[
        K.component(ids,'Sandbox.ModelRenderer','hall/bulkhead-lamp-native-v1/renderer',Model=MODEL,BodyGroups=18446744073709551615,RenderType='On',Tint='1,1,1,1')])
