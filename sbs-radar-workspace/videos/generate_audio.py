from pathlib import Path
import subprocess,json,concurrent.futures
R=Path(__file__).resolve().parent
cli=next(Path('/private/tmp/sbs-video-npm/_npx').glob('*/node_modules/hyperframes/package.json'))
pkg=json.loads(cli.read_text());binary=cli.parent/(pkg['bin'] if isinstance(pkg['bin'],str) else pkg['bin']['hyperframes'])
def run(p):
 out=p.with_suffix('.wav')
 if out.exists():return str(out)+' reused'
 result=subprocess.run(['node',str(binary),'tts',str(p),'--voice','ef_dora','--lang','es','--speed','0.95','-o',str(out),'--json'],capture_output=True,text=True)
 p.with_suffix('.log').write_text(result.stdout+result.stderr)
 if result.returncode:raise RuntimeError(str(p)+result.stderr[-700:])
 return result.stdout.strip()
with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
 for r in pool.map(run,sorted(R.glob('0*/assets/scene*.txt'))):print(r,flush=True)
