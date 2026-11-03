"""Sequential native s&box calls and exchange-directory scripts for this review."""
from pathlib import Path
import json,os,subprocess,sys,time,winreg

ROOT=Path(__file__).resolve().parents[3]
OUT=ROOT/'output/asset-improvement-20261030/tool-cabinet/native-review-20261031'
OUT.mkdir(parents=True,exist_ok=True)
engine=os.environ.get('FACEPUNCH_ENGINE')
if not engine:
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER,'Environment') as key:
            engine=winreg.QueryValueEx(key,'FACEPUNCH_ENGINE')[0]
    except FileNotFoundError:pass
if not engine:engine=str(Path(os.environ['ProgramFiles(x86)'])/'Steam/steamapps/common/sbox')
CLI=Path(engine)/'bin/managed/sbox-cli.exe'


def call(name,args):
    result=subprocess.run([str(CLI),'--call',name,json.dumps(args)],cwd=ROOT,capture_output=True,
                          text=True,encoding='utf-8',errors='replace',timeout=180)
    (OUT/f'{time.time_ns()}-{name}.txt').write_text(result.stdout+result.stderr,encoding='utf-8')
    if result.returncode:
        print(result.stdout+result.stderr);raise SystemExit(result.returncode)
    try:return json.loads(result.stdout)
    except json.JSONDecodeError:return result.stdout.rstrip()


class Client:
    def __init__(self):
        self.log=(OUT/f'{time.time_ns()}-mcp-stderr.txt').open('w',encoding='utf-8')
        self.process=subprocess.Popen([str(CLI),'--connect'],cwd=ROOT,stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,stderr=self.log,text=True,encoding='utf-8',bufsize=1,
            creationflags=subprocess.CREATE_NO_WINDOW)
        self.number=0
        self.initial=self.request('initialize',{'protocolVersion':'2025-11-25','capabilities':{},
            'clientInfo':{'name':'cabinet-comparison','version':'1'}})
        self.process.stdin.write(json.dumps({'jsonrpc':'2.0','method':'notifications/initialized'})+'\n')
        self.process.stdin.flush()
    def request(self,method,params):
        self.number+=1
        self.process.stdin.write(json.dumps({'jsonrpc':'2.0','id':self.number,'method':method,'params':params})+'\n')
        self.process.stdin.flush()
        while True:
            line=self.process.stdout.readline()
            if not line:raise RuntimeError('Native MCP connection ended')
            result=json.loads(line)
            if 'error' in result:raise RuntimeError(result['error'])
            if result.get('id')==self.number:return result['result']
    def tool(self,name,args):
        result=self.request('tools/call',{'name':name,'arguments':args})
        (OUT/f'{time.time_ns()}-{name}-mcp.json').write_text(json.dumps(result,indent=2)+'\n')
        if result.get('isError'):raise RuntimeError(result)
        if 'structuredContent' in result:return result['structuredContent']
        text='\n'.join(c['text'] for c in result.get('content',[]) if c['type']=='text')
        try:return json.loads(text)
        except json.JSONDecodeError:return text
    def close(self):
        self.process.stdin.close();self.process.wait(timeout=15);self.log.close()

def main():
    mode=sys.argv[1]
    if mode=='schema':
        name=sys.argv[2];result=call('search_tools',{'query':name})
        result=[t for t in result['tools'] if t['name']==name]
        assert len(result)==1,name
        (OUT/(name+'-schema.json')).write_text(json.dumps(result[0],indent=2)+'\n')
        print(json.dumps(result[0],indent=2))
    elif mode in ('script','handshake'):
        client=Client()
        try:
            if mode=='handshake':print(json.dumps(client.initial,indent=2))
            else:
                directory=Path(client.initial['_meta']['exchangeDirectory'])
                directory.mkdir(parents=True,exist_ok=True)
                path=directory/Path(sys.argv[2]).name
                path.write_bytes(Path(sys.argv[2]).read_bytes())
                print(json.dumps(client.tool('run_csharp',{'path':str(path)}),indent=2))
        finally:client.close()
    else:
        args=json.loads(Path(sys.argv[2]).read_text()) if len(sys.argv)>2 else {}
        print(json.dumps(call(mode,args),indent=2))

if __name__ == '__main__':
    main()
