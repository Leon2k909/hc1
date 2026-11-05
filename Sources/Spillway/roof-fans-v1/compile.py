import json
from native import call
for name in ('before','fan','spillway_west_preview','spillway_east_preview'):
 path=f'models/maps/spillway/roof-fans-v1/{name}.vmdl'
 info=call('asset_info',{'path':path})
 if not info.get('IsCompiledAndUpToDate'):print(json.dumps(call('asset_compile',{'path':path,'full':True})))
 info=call('asset_info',{'path':path});assert info['IsCompiledAndUpToDate'] and not info['IsCompileFailed'];print(name,'compiled')
