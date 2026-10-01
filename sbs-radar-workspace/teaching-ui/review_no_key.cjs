// No-key path with real extracted functions and a minimal DOM stand-in.
// Never loads the sidecar, localStorage, credentials, browser or network.
const fs=require('fs'),vm=require('vm'),assert=require('assert'),path=require('path');
const html=fs.readFileSync(path.join(__dirname,'index.html'),'utf8');
function fn(name){const m=html.match(new RegExp('  (?:async )?function '+name+'\\([^]*?\\n  }'));assert(m,name);return m[0];}
const data=JSON.parse(html.match(/<script id="foquito-datos" type="application\/json">([^]*?)<\/script>/)[1]);
const bubbles=[],prompts=[];let fetches=0,removed=false;
const env={D:data,sel:{id:'fq15'},P:{nombre:'Groq'},conversacion:[],TOPE_TURNOS:8,ultimaPregunta:null,ocupado:false,clave:()=>'',pintarSelector(){},bloquear(v){env.ocupado=v;},burbuja(cls,markup){bubbles.push(markup);},pedirClave(markup){prompts.push(markup);},fetch(){fetches++;throw Error('NETWORK_FORBIDDEN');}};
vm.createContext(env);vm.runInContext(['fmt','precomputada','preguntar','turno'].map(fn).join('\n'),env);
(async()=>{await env.turno('¿Qué es RRF?',{remove(){removed=true;}});assert.equal(fetches,0);assert(removed);assert.equal(env.ocupado,false);assert.equal(env.conversacion.length,0);assert.equal(bubbles.length,1);assert(bubbles[0].includes('El tutor local ayuda'));assert.equal(prompts.length,1);assert(prompts[0].includes('generada al construir la página'));console.log(JSON.stringify({status:'PASS_NO_KEY_DOM_MOCK',prepared_explanation_shown:true,no_live_answer_claimed:true,input_unblocked:true,network_calls:fetches,sidecar_read:false,real_browser_e2e:false}));})().catch(e=>{console.error(e);process.exitCode=1;});
