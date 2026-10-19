from pathlib import Path
import argparse
import json

folder=Path(__file__).resolve().parent
parser=argparse.ArgumentParser()
parser.add_argument('name')
parser.add_argument('--intensity',type=float)
parser.add_argument('--normal-bias',type=float)
parser.add_argument('--view-bias',type=float)
parser.add_argument('--disable-gi',action='store_true')
parser.add_argument('--views',nargs='*')
parser.add_argument('--minimum',type=float)
parser.add_argument('--maximum',type=float)
parser.add_argument('--fill',type=float,default=1.0)
args=parser.parse_args()
original=folder/'capture-base.json'
if not original.exists(): original.write_bytes((folder/'capture.json').read_bytes())
config=json.loads(original.read_text())
config['pass']=args.name
config['indirect']={'enabled':not args.disable_gi}
for key in ('intensity','normal_bias','view_bias'):
    if getattr(args,key) is not None: config['indirect'][key]=getattr(args,key)
if args.views: config['views']=[v for v in config['views'] if v['name'] in args.views]
if args.minimum is not None:
    config['trial']={'sun':'1.55,1.35,1.10,1','sky':'0.25,0.31,0.40,1',
                     'minimum':args.minimum,'maximum':args.maximum or args.minimum,'fill':args.fill}
(folder/'capture.json').write_text(json.dumps(config,indent=2),encoding='utf-8')
