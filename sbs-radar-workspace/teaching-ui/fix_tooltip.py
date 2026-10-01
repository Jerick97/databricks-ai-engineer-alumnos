from pathlib import Path
p=Path(__file__).with_name('index.html');s=p.read_text()
s=s.replace("Math.max(12,Math.min(r.bottom+8,innerHeight-hg-12))+'px'", "Math.max(12,(r.bottom+hg+20<=innerHeight?r.bottom+8:r.top-hg-8))+'px'")
s=s.replace("+' disposición'+(f.provisions.length>1?'es':'')", "+(f.provisions.length>1?' disposiciones':' disposición')")
p.write_text(s)
