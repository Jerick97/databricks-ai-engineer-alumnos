from pathlib import Path
from urllib.request import urlopen
import json,hashlib
R=Path(__file__).resolve().parent
urls={'gsap.min.js':'https://cdn.jsdelivr.net/npm/gsap@3.14.2/dist/gsap.min.js','Montserrat.ttf':'https://raw.githubusercontent.com/google/fonts/main/ofl/montserrat/Montserrat%5Bwght%5D.ttf','JetBrainsMono.ttf':'https://raw.githubusercontent.com/google/fonts/main/ofl/jetbrainsmono/JetBrainsMono%5Bwght%5D.ttf'}
ledger=[]
for name,url in urls.items():
 data=urlopen(url,timeout=40).read()
 for p in R.glob('0*/assets'):(p/name).write_bytes(data)
 ledger.append({'file':name,'source':url,'sha256':hashlib.sha256(data).hexdigest(),'bytes':len(data)})
(R/'asset-provenance.json').write_text(json.dumps(ledger,indent=2))
print('3 recursos congelados localmente para ambos videos')
