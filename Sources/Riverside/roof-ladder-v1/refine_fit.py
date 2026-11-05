from pathlib import Path
p=Path(__file__).parent/'build.py';s=p.read_text();s=s.replace("f'P(240,n,{H+1})'","'P(240,n,roof(n)+1.0)'").replace("f'box(240,n,{H+.6}'","'box(240,n,roof(n)+.6'").replace("f'P(240,n+offset,{H+1.21}),P(240,n+offset,{H+1.5})'","'P(240,n+offset,roof(n+offset)+1.21),P(240,n+offset,roof(n+offset)+1.5)'")
s=s.replace("env=dict(A.__dict__);exec", "env=dict(A.__dict__);env['roof']=lambda n:H-1-5.5*abs(40+n)/62.5;exec")
p.write_text(s,encoding='utf-8')
