"""Select the existing brushed finish on only the new proposal's metal faces."""
from pathlib import Path
here=Path(__file__).parent;path=here/'build.py';text=path.read_text();index=text.index('legacy=K.Model();')
head=text[:index].replace("'rw_steel'","'rw_stainless'")
path.write_text(head+text[index:])
readme=here/'README.md';text=readme.read_text().replace('Existing Railhead steel, dark-steel, black and yellow materials only','Existing Railhead brushed stainless, dark-steel, black and yellow materials only');readme.write_text(text)
print('New model uses the existing stainless finish; legacy source matcher unchanged')
