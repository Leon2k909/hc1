from native import call
for name in ('before','stack','props_preview'):
 p='models/maps/boxyard/pallet-stack-v1/'+name+'.vmdl'
 i=call('asset_info',{'path':p})
 if not i['IsCompiledAndUpToDate']:print(call('asset_compile',{'path':p,'full':True}),flush=True)
 print(name,call('asset_info',{'path':p})['IsCompiledAndUpToDate'],flush=True)
