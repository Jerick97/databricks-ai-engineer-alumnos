from pathlib import Path
p=Path(__file__).with_name('index.html')
s=p.read_text()
bridge='''
  // SBS teaching adapter: scoped to this artifact, no Databricks requests.
  SYS += '\\nEres el tutor de una réplica didáctica, no el agente operativo. No afirmes haber ejecutado RAG, Genie ni consultas actuales. No confirmes vigencia ni obligaciones a partir de extractos parciales. Explica límites y fuentes disponibles.';
  window.openSbsTutor = function(question, context) {
    if (ocupado) { panel.classList.add('fq-abierto'); return; }
    if (!sel || sel.id !== 'fq15' || sel.parrafo !== context) {
      conversacion=[]; hilo.innerHTML=''; limpiarMarcas();
    }
    sel={texto:'Tutor de SBS Radar · selección actual',id:'fq15',parrafo:context};
    elSel.textContent=sel.texto;
    panel.classList.add('fq-abierto'); panel.setAttribute('aria-hidden','false');
    pintarSelector(); pintarEstado();
    burbuja('fq-yo',fmt(question)); turno(question,pensando());
  };
'''
needle='  function arrancar(s) {'
assert needle in s
s=s.replace(needle,bridge+'\n'+needle)
s=s.replace("burbuja('', '<div class=\"fq-aviso\">' + r.error + '</div>');", "burbuja('', '<div class=\"fq-aviso\">' + fmt(r.error) + '</div>');\n      var respaldo=precomputada(); if(respaldo) burbuja('', '<small>Explicación preparada · sin respuesta en vivo</small><br>'+respaldo);")
p.write_text(s)
print('Tutor integrado; clave fuera del HTML')
