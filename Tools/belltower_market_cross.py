import map_kit as K
MODEL='models/maps/belltower/market-cross-v2/market_cross.vmdl'
def group(ids):
    key='market_cross'
    child=K.game_object(ids,'Market cross',key,K.to_world((0,1275,0)),components=[K.component(ids,'Sandbox.ModelRenderer',key+'/renderer',Model=MODEL,RenderType='On',Tint='1,1,1,1')])
    return K.game_object(ids,'Market cross model',key+'/group',children=[child])
