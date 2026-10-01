from pathlib import Path
p=Path(__file__).with_name('index.html');s=p.read_text()
needle='    ultimaPregunta = pregunta;'
insert='''    // Verifiable UI facts are answered from the artifact contract, not guessed.
    var normalized=pregunta.normalize('NFD').replace(/[\\u0300-\\u036f]/g,'').toLowerCase();
    var fact=null;
    if(/version|opcion|par documental/.test(normalized) && /una sola|una opcion|solo hay|cuantas|cuantos/.test(normalized)) fact='**Una opción representa un par de dos copias documentales: A y B.** Esta guía incluye un par por familia. El selector no cuenta versiones individuales; la disposición elige un artículo dentro del par. No permite concluir cuántas versiones existen fuera de esta muestra.';
    if(/actualizar|refrescar/.test(normalized) && /catalogo|version|par|guia/.test(normalized)) fact='**En esta guía local, Actualizar catálogo sólo muestra una explicación.** No lee un repositorio, no añade pares, no descarga versiones ni ejecuta un Job. En el agente real el control relee el corpus publicado; ese comportamiento es distinto del de esta réplica.';
    if(fact){
      ultimaPregunta=pregunta; conversacion.push({role:'user',content:pregunta},{role:'assistant',content:fact});
      cargando.remove(); burbuja('',fmt(fact)+'<p class="fq-pie">Hecho verificado de la interfaz · respuesta preparada, sin llamada al modelo</p>');
      bloquear(false); pintarSelector(); input.focus(); return;
    }
'''
assert needle in s;s=s.replace(needle,insert+needle)
p.write_text(s)
print('Hechos de controles protegidos contra inferencias del modelo')
