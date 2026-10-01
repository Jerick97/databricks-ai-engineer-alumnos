from pathlib import Path
import json,wave,subprocess,hashlib,struct
R=Path(__file__).resolve().parent
for p in sorted(R.glob('0*')):
 if not p.is_dir():continue
 timing=json.loads((p/'timing.json').read_text()); script=json.loads((p/'script.json').read_text());rate=24000;pcm=bytearray();audit=[]
 for c in timing['chapters']:
  f=p/'assets'/f"{c['id']}.wav"
  with wave.open(str(f)) as w:
   assert w.getframerate()==rate and w.getnchannels()==1 and w.getsampwidth()==2
   b=w.readframes(w.getnframes())
  pcm.extend(b'\x00'*max(0,(round((c['start']+.35)*rate)-len(pcm)//2)*2));pcm.extend(b)
  values=struct.unpack('<'+'h'*(len(b)//2),b)
  peak=max(abs(n) for n in values);audit.append({'id':c['id'],'seconds':len(values)/rate,'peak':peak,'clipped_samples':sum(abs(n)>=32767 for n in values),'non_silent':peak>100,'sha256':hashlib.sha256(f.read_bytes()).hexdigest()})
 pcm.extend(b'\x00'*max(0,(round(timing['duration']*rate)-len(pcm)//2)*2))
 with wave.open(str(p/'narracion-dora.wav'),'wb') as w:w.setparams((1,2,rate,0,'NONE','not compressed'));w.writeframes(pcm)
 subprocess.run(['ffmpeg','-y','-v','error','-i',str(p/'narracion-dora.wav'),'-c:a','aac','-b:a','128k',str(p/'narracion-dora.m4a')],check=True)
 (p/'audio-validation.json').write_text(json.dumps({'provider':'local Kokoro','voice':'ef_dora','language':'es','speed':.95,'duration':timing['duration'],'technical_checks':audit,'perceptual_listening':'not claimed'},indent=2))
 (p/'guion.txt').write_text('\n\n'.join(f"{i+1}. {s['title']}\n{s['narration']}" for i,s in enumerate(script['scenes'])))
 (p/'VALIDATION.md').write_text('''# Estado de entrega
Guion: revisión independiente PASS (../script-review.json).
Voz: Kokoro ef_dora, español, 0.95; seis archivos WAV más narración completa WAV/M4A. Duraciones medidas, audio no vacío y picos comprobados.
Composición: HyperFrames 0.8.98, 1920x1080, seis subcomposiciones. Ver lint/check JSON.
Render MP4: PENDIENTE. La sesión restringida de macOS impide iniciar Chromium: MachPortRendezvous / bootstrap_check_in Permission denied (1100).
Layout, contraste y montaje visual todavía NO acreditados. No interpretar muestras=0 como PASS.
No se modificó infraestructura Databricks ni se ejecutaron sus pipelines.
''')
print('Audios completos y evidencia guardados')
