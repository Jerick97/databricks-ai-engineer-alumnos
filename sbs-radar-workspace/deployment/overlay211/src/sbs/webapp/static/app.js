'use strict';
const $=id=>document.getElementById(id);
const state={catalog:null,csrf:'',pair:null,provision:null,revision:0,messages:[],busy:false,snapshot:null};
function text(id,value){$(id).textContent=value||'';}
function node(tag,value,className){const e=document.createElement(tag);e.textContent=value||'';if(className)e.className=className;return e;}
const labels={partial:'Evidencia parcial',unreviewed:'Pendiente de revisión',proposed:'Propuesta · sin aprobación',answered:'Respuesta IA · pendiente de revisión',conflict:'Fuentes en conflicto',insufficient_evidence:'Evidencia insuficiente',generation_error:'Consulta no disponible',denied:'Acceso no autorizado',structured_response_pending:'Respuesta pendiente de estructuración',answered_structured:'Conteo documental verificado',structured_result_unavailable:'Consulta documental no disponible',scope_not_answered:'La consulta requiere otro alcance'};
function statusLabel(value){return labels[value]||value||'Pendiente de revisión';}
function sourceLink(c){const a=node('a',c.label||'Abrir fuente original','citation');a.href='/api/sources/'+encodeURIComponent(c.source_id);if(Number.isInteger(c.page)&&c.page>0)a.href+='#page='+c.page;a.target='_blank';a.rel='noopener noreferrer';return a;}
function citations(parent,items){for(const c of items||[]){if(c.source_id)parent.append(sourceLink(c));if(c.excerpt)parent.append(node('p',c.excerpt,'muted'));}}
async function api(path,options={}){
  const controller=new AbortController();const timer=setTimeout(()=>controller.abort(),120000);
  const invalid='El servicio no devolvió el formato esperado. Guarda tu pregunta y recarga la aplicación; si continúa, contacta al administrador.';
  try{
    let r;
    try{r=await fetch(path,{...options,signal:controller.signal,redirect:'manual'});}
    catch(e){if(e.name==='AbortError')throw e;throw Error('No se pudo conectar con el servicio. Revisa tu conexión y el estado de la aplicación antes de volver a enviar la consulta.');}
    if(r.type==='opaqueredirect'||r.redirected||(r.status>=300&&r.status<400))throw Error('La solicitud fue redirigida. Guarda tu pregunta y abre de nuevo la aplicación para comprobar tu sesión antes de volver a enviarla.');
    if(r.status===401)throw Error('No se pudo validar tu sesión. Guarda tu pregunta e inicia sesión de nuevo en la aplicación.');
    if(r.status===403)throw Error('La solicitud fue rechazada por permisos o por la protección de sesión. Guarda tu pregunta y recarga la aplicación; si continúa, contacta al administrador.');
    if(r.status===409)throw Error('La sesión de consultas no permite esta operación. Contacta al administrador para revisar su activación o cupo; las fuentes y comparaciones siguen disponibles.');
    if(!r.ok)throw Error(r.status===429?'El servicio alcanzó su límite de solicitudes (HTTP 429). Espera antes de volver a enviar tu consulta.':r.status>=500?`El servicio no está disponible (HTTP ${r.status}). Espera y comprueba el estado de la aplicación antes de volver a enviar tu consulta.`:`No fue posible completar la consulta (HTTP ${r.status}). Guarda tu pregunta y recarga la aplicación; si continúa, contacta al administrador.`);
    const type=(r.headers.get('Content-Type')||'').split(';')[0].trim().toLowerCase();
    if(!/^application\/(?:json|[a-z0-9!#$&^_.+-]+\+json)$/.test(type))throw Error(invalid);
    let data;
    try{data=await r.json();}catch(e){if(e.name==='AbortError')throw e;throw Error(invalid);}
    if(data===null||typeof data!=='object'||Array.isArray(data))throw Error(invalid);
    return data;
  }catch(e){if(e.name==='AbortError')throw Error('La consulta superó el tiempo de espera. Puedes reintentar; el servicio podría seguir procesándola.');throw e;}
  finally{clearTimeout(timer);}
}
function panel(id){for(const e of document.querySelectorAll('main>section'))e.hidden=e.id!==id;for(const b of document.querySelectorAll('[data-panel]')){if(b.dataset.panel===id)b.setAttribute('aria-current','page');else b.removeAttribute('aria-current');}if(id==='compare')loadComparison();}
for(const b of document.querySelectorAll('[data-panel]'))b.addEventListener('click',()=>panel(b.dataset.panel));
$('discuss').addEventListener('click',()=>{panel('chat');$('question').focus();});
function options(id,items,placeholder){const el=$(id);el.replaceChildren();if(placeholder){const o=node('option',placeholder);o.value='';el.append(o);}for(const item of items){const o=node('option',item.label||item.title||item.id);o.value=item.id;el.append(o);}}
function current(){return state.catalog.pairs.find(p=>p.id===$('pair').value);}
function contextChanged(){state.pair=$('pair').value;state.provision=$('provision').value||null;state.revision++;const p=current();text('chat-context',p?`${p.title} · ${$('provision').selectedOptions[0]?.textContent||'Sin disposición disponible'}`:'Sin selección');renderMessages();if(!$('compare').hidden)loadComparison();}
function pairChanged(){options('provision',current()?.provisions||[]);contextChanged();}
function familyChanged(){options('pair',state.catalog.pairs.filter(p=>p.family_id===$('family').value));pairChanged();renderCards();}
$('family').addEventListener('change',familyChanged);$('pair').addEventListener('change',pairChanged);$('provision').addEventListener('change',contextChanged);
function renderCards(){$('cards').replaceChildren();const pairs=state.catalog.pairs.filter(p=>p.family_id===$('family').value);if(!pairs.length)$('cards').append(node('p','No hay comparaciones disponibles para esta familia.'));for(const p of pairs){const card=node('article',null,'card');card.append(node('span',statusLabel(p.evidence_status),'badge'),node('span','Pendiente de revisión','badge'),node('h3',p.title),node('p',`${p.before_label||'Versión anterior'} → ${p.after_label||'Versión posterior'}`),node('p','Vigencia no confirmada · consulta los originales','muted'));const b=node('button','Examinar comparación →');b.addEventListener('click',()=>{$('pair').value=p.id;pairChanged();panel('compare');});card.append(b);if(p.identity_details){const detail=node('details');detail.append(node('summary','Identificadores de las copias'));const names={pair_id:'Comparación',before_document_id:'Documento A',after_document_id:'Documento B',before_version_id:'SHA-256 de copia A',after_version_id:'SHA-256 de copia B'};for(const [key,label] of Object.entries(names)){if(typeof p.identity_details[key]==='string')detail.append(node('p',label+': '+p.identity_details[key]));}card.append(detail);}$('cards').append(card);}}
async function loadComparison(){const revision=state.revision,snapshot=state.snapshot;if(!state.pair)return;const query=new URLSearchParams({pair_id:state.pair});if(state.provision)query.set('provision_id',state.provision);text('status','Cargando comparación…');text('before-text','');text('after-text','');text('summary','');text('limitations','');text('comparison-state','Cargando evidencia…');$('comparison-citations').replaceChildren();for(const side of ['before','after']){$(side+'-source').replaceChildren();text(side+'-label','');}try{const c=await api('/api/comparison?'+query);if(revision!==state.revision)return;if(c.snapshot&&c.snapshot!==snapshot){text('comparison-state','Los datos cambiaron. Actualiza el catálogo antes de comparar.');text('status','Actualiza el catálogo para usar la publicación disponible.');return;}text('comparison-title',c.title||current().title);text('comparison-state',`${statusLabel(c.evidence_status)} · ${statusLabel(c.status)} · Vigencia no confirmada`);for(const side of ['before','after']){text(side+'-label',c[side]?.label);text(side+'-text',c[side]?.text||'No hay pasaje disponible para esta selección.');if(c[side]?.source_id)$(side+'-source').append(sourceLink(c[side]));}text('summary',c.summary||'Sin síntesis disponible. Consulta la evidencia original.');citations($('comparison-citations'),c.citations);text('limitations',(c.limitations||[]).join(' · '));text('status','Comparación cargada. La interpretación está pendiente de revisión.');}catch(e){if(revision!==state.revision)return;text('status',e.message);text('comparison-state','Consulta no disponible. Cambia la selección o vuelve a Comparación para reintentar.');}}
function structuredResults(parent,results){
  if(!Array.isArray(results))return;
  for(const result of results){
    if(result?.kind!=='documentary_count')continue;
    const detail=node('details');detail.append(node('summary','Ver consulta, alcance y fuentes del conteo'));
    detail.append(node('p',result.meaning),node('p','Consulta: '+result.query_id+' · Disposición: '+(result.context?.selected_provision_id||'Par documental')));
    const table=node('table');const header=node('tr');for(const col of result.columns||[])header.append(node('th',String(col)));table.append(header);
    for(const values of result.rows||[]){const row=node('tr');for(const value of values)row.append(node('td',String(value)));table.append(row);}detail.append(table);
    for(const side of ['before','after']){const source=result.context?.pair?.[side];if(source?.version_id)detail.append(sourceLink({source_id:source.version_id,label:(side==='before'?'Original anterior':'Original posterior')+' · '+source.document_id}));}
    detail.append(node('pre',result.query),node('p','Snapshot documental: '+result.snapshot,'muted'));parent.append(detail);
  }
}
function assistantPresentation211(content){
  let omitted=0;
  // Only whole, explicitly delimited replacements with two whitespace-only sides.
  const empty=/^Texto reemplazado \(fragmentos literales\):\r?\nAntes:\r?\n\s*Después:\r?\n\s*(?=^Texto (?:reemplazado \(fragmentos literales\)|añadido \(fragmento literal\)|eliminado \(fragmento literal\)):|(?![\s\S]))/gm;
  const display=content.replace(empty,()=>{omitted++;return '';});
  return {display,omitted};
}
function appendMessageContent211(box,message){
  const presented=message.role==='assistant'?assistantPresentation211(message.content):{display:message.content,omitted:0};
  box.append(node('div',presented.display));
  if(presented.omitted){
    box.append(node('p','Se omitieron de esta vista '+presented.omitted+' bloques que solo contienen espacios o saltos de línea. La respuesta completa se conserva.','muted'));
    const raw=node('details');raw.append(node('summary','Ver respuesta completa, incluidos los espacios'),node('pre',message.content));box.append(raw);
  }
}
function renderMessages(){$('messages').replaceChildren();const items=state.messages.filter(m=>m.pair===state.pair&&m.provision===state.provision&&m.snapshot===state.snapshot);if(!items.length)$('messages').append(node('p','Empieza una conversación sobre la selección actual.','muted'));for(const m of items){const box=node('article',null,'message '+m.role);box.append(node('strong',m.role==='user'?'TÚ':statusLabel(m.status)));appendMessageContent211(box,m);citations(box,m.citations);structuredResults(box,m.structured_results);if(m.limitations?.length)box.append(node('p',m.limitations.join(' · '),'muted'));$('messages').append(box);}}
$('question-form').addEventListener('submit',async e=>{e.preventDefault();const question=$('question').value.trim();if(!question||state.busy||!state.pair)return;state.busy=true;$('send').disabled=true;const pair=state.pair,provision=state.provision,snapshot=state.snapshot;state.messages.push({role:'user',content:question,pair,provision,snapshot});renderMessages();text('status','Consultando evidencia…');try{const a=await api('/api/ask',{method:'POST',headers:{'Content-Type':'application/json','X-CSRF-Token':state.csrf},body:JSON.stringify({question,pair_id:pair,provision_id:provision,cross_family:$('cross').checked})});if(a.snapshot&&a.snapshot!==snapshot){text('status','Los datos cambiaron durante la consulta. Actualiza el catálogo y vuelve a preguntar.');return;}state.messages.push({role:'assistant',content:a.answer||'No hay respuesta disponible. Revisa las limitaciones indicadas.',status:a.status,citations:a.citations,structured_results:a.structured_results,limitations:a.limitations,pair,provision,snapshot});text('status',statusLabel(a.status));if(state.pair===pair&&state.provision===provision)$('question').value='';}catch(err){state.messages.push({role:'assistant',content:err.message,status:'generation_error',pair,provision,snapshot});text('status','La consulta no se completó. Puedes reintentar.');}finally{state.busy=false;$('send').disabled=false;renderMessages();}});
function renderFreshness(catalog){
  const r=catalog.runtime_refresh;
  if(!r?.enabled){text('freshness','Corpus disponible de la entrega · actualización automática no habilitada.');return;}
  const copy={pending:'Comprobación de datos publicados pendiente.',current:'Se consultó la publicación disponible. Esto no confirma vigencia normativa.',unavailable:'No se pudo comprobar la nueva publicación. Se conservan los datos anteriores.',error:'No se pudo comprobar la nueva publicación. Se conservan los datos anteriores.',unchanged:'La publicación consultada conserva el mismo conjunto de datos.',quota_exhausted:'Se alcanzó el límite de comprobaciones. Se conservan los datos disponibles.'};
  text('freshness',copy[r.status]||'Estado de actualización pendiente de verificación. Se conservan los datos disponibles.');
}
async function refreshCatalog(){
  const selected={family:$('family').value,pair:state.pair,provision:state.provision};
  const previous=state.snapshot;
  const c=await api('/api/catalog');
  state.catalog=c;state.csrf=c.csrf_token;state.snapshot=c.snapshot||null;
  options('family',c.families||[]);
  if((c.families||[]).some(f=>f.id===selected.family))$('family').value=selected.family;
  const pairs=c.pairs.filter(p=>p.family_id===$('family').value);
  options('pair',pairs);
  if(pairs.some(p=>p.id===selected.pair))$('pair').value=selected.pair;
  const provisions=current()?.provisions||[];
  options('provision',provisions);
  if(provisions.some(p=>p.id===selected.provision))$('provision').value=selected.provision;
  text('session',c.session_mode);renderFreshness(c);contextChanged();renderCards();
  text('status',previous&&previous!==state.snapshot?'Se actualizaron los datos. Revisa la selección antes de consultar; el historial anterior no se mezcla con esta versión.':(c.pairs.length?'Catálogo disponible · selecciona una comparación.':'No hay datos disponibles en esta configuración.'));
}
$('refresh-catalog').addEventListener('click',async()=>{
  if(state.busy)return;
  state.busy=true;$('refresh-catalog').disabled=true;$('send').disabled=true;
  try{await refreshCatalog();}catch(e){text('status',e.message);text('freshness','No se pudo actualizar el catálogo. Se conserva la selección anterior.');}
  finally{state.busy=false;$('refresh-catalog').disabled=false;$('send').disabled=false;}
});
async function init(){try{await refreshCatalog();}catch(e){text('status',e.message);$('send').disabled=true;}}
init();

// Operator actions remain visible and explicit; no polling or automatic activation.
async function runtimeStatus210(){
  const r=await api('/api/runtime/status');
  $('runtime-epoch').value=r.epoch;
  const descriptions={inactive:'Consultas sin activar. Las fuentes y comparaciones están disponibles.',active:'Consultas activas.',expired:'La sesión de consultas venció.',exhausted:'La asignación de consultas se agotó.'};
  text('runtime-status',(descriptions[r.state]||'Estado no disponible.')+' Generación: '+r.used.generation_posts+'/'+r.caps.generation_posts+'; embeddings: '+r.used.embedding_posts+'/'+r.caps.embedding_posts+'.');
  return r;
}
$('runtime-refresh').addEventListener('click',async()=>{
  $('runtime-refresh').disabled=true;
  try{await runtimeStatus210();}catch(e){text('runtime-status',e.message);}finally{$('runtime-refresh').disabled=false;}
});
$('runtime-activation-form').addEventListener('submit',async e=>{
  e.preventDefault();$('runtime-activate').disabled=true;
  try{
    let allocation;
    try{allocation=JSON.parse($('runtime-activation').value);}catch{throw Error('La asignación no contiene JSON válido. Copia el documento completo del coordinador.');}
    await api('/api/runtime/activate',{method:'POST',headers:{'Content-Type':'application/json','X-CSRF-Token':state.csrf},body:JSON.stringify(allocation)});
    $('runtime-activation').value='';
    await runtimeStatus210();
  }catch(e){text('runtime-status',e.message+' Consulta el estado antes de intentar otra activación.');}
  finally{$('runtime-activate').disabled=false;}
});
