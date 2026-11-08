from pathlib import Path
import shutil,json
out=Path('C:/sbox-projects/hc1/forked-shooter-main/output/cerroblanco/courtyard-bin-v1')
shutil.copyfile('C:/Users/leon2/AppData/Local/Temp/bridge_window_152920_047.png',out/'after-joints.png')
report={'previous_post_centre_radius':7.15,'previous_post_radius':.32,'liner_inner_radius':7.96,'previous_radial_gap':.49,'revised_post_centre_radius':8.5,'revised_post_radius':.32,'rim_top_radial_interval':[8.35,8.65],'revised_post_radial_interval':[8.18,8.82],'post_height_interval':[25.8,32.55],'rim_top_height':26.9,'hood_underside_height':32.25,'lower_socket_radius':.47,'upper_socket_radius':.43,'native_closeup':'after-joints.png','original_map_bin_restored':True}
assert max(report['revised_post_radial_interval'][0],report['rim_top_radial_interval'][0])<min(report['revised_post_radial_interval'][1],report['rim_top_radial_interval'][1])
assert report['post_height_interval'][0]<report['rim_top_height']<report['hood_underside_height']<report['post_height_interval'][1]
(out/'joint-checks.json').write_text(json.dumps(report,indent=2));print(report)
