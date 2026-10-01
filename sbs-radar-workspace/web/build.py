from pathlib import Path
import json,re
p=Path(__file__).resolve().parent
items=json.loads((p/'frameworks.json').read_text())+json.loads((p/'decisions.json').read_text())
assert len(items)==30 and len({x['id'] for x in items})==30
ids={x['id'] for x in items}
for x in items:
    for k in ['id','group','title','tagline','what','see','options','evidence','mistake','question','sbs','links']:assert x.get(k), (x['id'],k)
    assert len(x['options'])>=3
    assert set(x['links'])<=ids,(x['id'],x['links'])
    for o in x['options']:assert all(o.get(k) for k in ['name','when','tradeoff'])
template=(p/'template.html').read_text()
data=json.dumps(items,ensure_ascii=False).replace('<','\\u003c')
(p/'index.html').write_text(template.replace('__COURSE_DATA__',data))
scripts=re.findall(r'<script>(.*?)</script>',template,re.S)
(p/'check.js').write_text('\n'.join(scripts))
print(json.dumps({'items':len(items),'groups':{g:sum(x['group']==g for x in items) for g in ['layers','stages','decisions']},'bytes':(p/'index.html').stat().st_size}))
