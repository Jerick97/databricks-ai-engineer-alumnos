// Structural execution tests with a minimal DOM double. These are not browser/UI tests.
const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const path=require('node:path'),root=__dirname;
const data=[...JSON.parse(fs.readFileSync(path.join(root,'frameworks.json'))),...JSON.parse(fs.readFileSync(path.join(root,'decisions.json')))];
const nodes={},handlers={},storage={};
function node(id){return nodes[id]??=( {textContent:'',innerHTML:'',hidden:true,setAttribute(){},removeAttribute(){},classList:{toggle(){}}} );}
node('course-data').textContent=JSON.stringify(data);
const context=vm.createContext({document:{getElementById:node,querySelector:node,querySelectorAll:()=>[],body:node('body'),addEventListener:(k,fn)=>handlers[k]=fn},localStorage:{getItem:k=>storage[k]||null,setItem:(k,v)=>storage[k]=v},location:{hash:''},history:{replaceState(){}},window:{scrollTo(){},addEventListener(){},print(){}},setTimeout:()=>1,clearTimeout(){},console});
vm.runInContext(fs.readFileSync(path.join(root,'check.js'),'utf8'),context);
const run=s=>vm.runInContext(s,context);
assert.ok(node('main').innerHTML.includes('Un agente empieza'));
let rendered=0;
for(const item of data){run(`openItem(${JSON.stringify(item.id)})`);assert.ok(node('main').innerHTML.includes(item.title));assert.ok(node('main').innerHTML.includes('Qué opciones tienes'));assert.ok(node('main').innerHTML.includes('Aplicado al agente SBS'));rendered++;}
run("state.teacher=true;render()");assert.ok(node('main').innerHTML.includes('Pregunta para el grupo'));
run("state.group='layers';state.query='recuperación'");assert.ok(run('filtered().some(x=>x.id===\'L5\')'));
run("state.query='zzzzzzzz'");assert.equal(run('filtered().length'),0);
for(const view of ['home','explore','matrix','sbs','sources']){run(`goto('${view}')`);assert.ok(node('main').innerHTML.length>500);assert.ok(!node('main').innerHTML.includes('undefined'));}
for(let i=0;i<4;i++){run(`state.scenario=${i};state.answer=SCENARIOS[${i}].correct;goto('sbs')`);assert.ok(node('main').innerHTML.includes('Correcto:'));run(`state.answer=(SCENARIOS[${i}].correct+1)%3;render()`);assert.ok(node('main').innerHTML.includes('Revisa el salto'));}
run("openItem('A01')");handlers.input({target:{id:'notes',value:'Prueba temporal de persistencia'}});handlers.change({target:{id:'read',checked:true}});
assert.equal(JSON.parse(storage['aula-sbs-v1']).notes.A01,'Prueba temporal de persistencia');assert.equal(JSON.parse(storage['aula-sbs-v1']).read.A01,true);
assert.equal(run("esc('<script>')"),'&lt;script&gt;');
console.log(JSON.stringify({status:'PASS',itemsRendered:rendered,views:5,scenariosWithCorrectAndIncorrectFeedback:4,search:true,teacherMode:true,notesStorageDouble:true,htmlEscaping:true,scope:'Node VM + DOM double; not visual/browser verification'}));
