import subprocess,json,time
CLI='C:/Program Files (x86)/Steam/steamapps/common/sbox/bin/managed/sbox-cli.exe'
def call(name,args):
    p=subprocess.run([CLI,'--call',name,json.dumps(args)],text=True,capture_output=True)
    if p.returncode:raise RuntimeError(p.stderr)
    return p.stdout.strip()
print(call('switch_scene',{'scene':'scenes/maps/cerroblanco/cerroblanco.scene'}));time.sleep(.7)
print(call('set_editor_camera',{'position':'760,-2110,180','angles':'-14,130,0'}));time.sleep(.7)
print(call('bridge_call',{'command':'screenshot_game','parameters':{'crop':{'x':650,'y':215,'w':650,'h':550}}}))
