// Read-only payload review; no sidecar, browser, credentials or network.
const fs=require('fs'),vm=require('vm'),assert=require('assert');
const path=require('path');
const html=fs.readFileSync(path.join(__dirname,'index.html'),'utf8');
function fn(name){const m=html.match(new RegExp('  function '+name+'\\([^]*?\\n  }'));assert(m,name);return m[0];}
const bridge=html.match(/  window\.openSbsTutor = function\(question, context\) \{[^]*?\n  };/)[0];
const tutor=html.match(/function tutorContext\(\)\{[^\n]+/)[0];
const provisions=JSON.parse(html.match(/const PROVISIONS=([^]*?);\nconst APP=/)[1]);
const captures=[];let selected=0,cross=false;
const env={window:{},sel:null,ocupado:false,conversacion:[],hilo:{innerHTML:''},elSel:{},panel:{inert:true,classList:{add(){}},setAttribute(){}},limpiarMarcas(){},pintarSelector(){},pintarEstado(){},burbuja(){},fmt:x=>x,pensando:()=>({}),TOPE_VECINDAD:1800,TOPE_CONTEXTO:2500,TOPE_MAPA:1400,D:{contexto:'Replica didactica'},mapaDocumento:()=>'',document:{querySelectorAll:()=>[{dataset:{fq:'fq15'},textContent:'Generic static help'}]},family:()=>selected===0?{label:'Ciberseguridad',norm:'504-2021'}:{label:'Conducta de mercado',norm:'3274-2017'},provision:()=>provisions[selected],$:()=>({checked:cross})};
vm.createContext(env);vm.runInContext(fn('vecindad')+'\n'+fn('material')+'\n'+tutor+'\n'+bridge,env);
env.turno=q=>captures.push({question:q,material:env.material()});
selected=0;env.window.openSbsTutor('Pregunta cyber',env.tutorContext());
assert(captures[0].material.includes('Artículo 20.3'));assert(captures[0].material.includes(provisions[0].before.slice(0,100)));
selected=2;cross=true;env.window.openSbsTutor('Pregunta mercado',env.tutorContext());
assert(captures[1].material.includes('Artículo 29.1.4'));assert(captures[1].material.includes('ambas familias'));assert(captures[1].material.includes(provisions[2].after.slice(0,100)));assert(!captures[1].material.includes('Artículo 20.3'));
assert(captures[1].material.includes('Extractos parciales'));assert(captures[1].material.includes('No deducir ausencia'));
let parsed=0;for(const m of html.matchAll(/<script\b([^>]*)>([^]*?)<\/script>/g)){if(m[1].includes('application/json')||m[1].includes(' src='))continue;new vm.Script(m[2]);parsed++;}
console.log(JSON.stringify({status:'PASS',two_selection_payloads:2,cross_scope_present:true,partial_context_limit_present:true,inline_scripts_syntax_checked:parsed,network_calls:0,sidecar_read:false}));
