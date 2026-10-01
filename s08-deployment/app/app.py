"""UI servidor: el navegador nunca recibe credenciales Databricks."""
import os
import uuid
from flask import Flask, request, render_template_string
from databricks.sdk import WorkspaceClient
app=Flask(__name__)
app.config['MAX_CONTENT_LENGTH']=12000
PAGE='''<!doctype html><html lang="es"><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>Neptuno · S08</title>
<style>body{font:18px system-ui;max-width:820px;margin:50px auto;padding:24px;color:#123}textarea{box-sizing:border-box;width:100%;height:110px;font:inherit}button{font:inherit;padding:12px;background:#e44332;color:white;border:0}pre{white-space:pre-wrap;overflow-wrap:anywhere;line-height:1.6;background:#f2f5f7;padding:20px}</style>
<h1>Copiloto de Datos Neptuno</h1><p>Consulta ventas por categoría y año, reposición o políticas documentadas.</p>
<form method="post"><label for="q">Pregunta</label><textarea id="q" name="question" maxlength="2000" required>{{ question }}</textarea><p><button>Consultar</button></p></form>
{% if answer %}<h2>Respuesta</h2><pre>{{ answer }}</pre>{% endif %}
<p>Acceso corporativo mediante Databricks Apps. El servidor consulta con la identidad de la App, no con los permisos individuales del usuario. No ingreses datos personales ni secretos.</p></html>'''
@app.route('/',methods=['GET','POST'])
def index():
    answer='';question=''
    if request.method=='POST':
        question=request.form.get('question','').strip()
        if not question or len(question)>2000:
            return render_template_string(PAGE,question=question[:2000],answer='Pregunta vacía o demasiado larga. Escribe entre 1 y 2000 caracteres y vuelve a intentar.'),400
        try:
            w=WorkspaceClient()
            result=w.api_client.do('POST',f"/serving-endpoints/{os.environ['SERVING_ENDPOINT']}/invocations",body={'input':[{'role':'user','content':question}], 'client_request_id':str(uuid.uuid4())})
            answer='\n'.join(part.get('text','') for item in result.get('output',[]) for part in item.get('content',[]) if part.get('type')=='output_text') or 'Respuesta sin texto; revisa el endpoint.'
        except Exception:
            answer='La consulta no pudo completarse. Revisa el estado del endpoint con el instructor.'
    return render_template_string(PAGE,question=question,answer=answer)
@app.get('/health')
def health():return {'status':'ok'}
