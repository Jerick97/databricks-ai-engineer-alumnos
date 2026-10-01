const assert = require('node:assert/strict');
const {test} = require('node:test');
const {readFileSync} = require('node:fs');
const vm = require('node:vm');
const source = readFileSync('src/sbs/webapp/static/app.js', 'utf8');
// Evaluate production helper declarations only; do not initialize the UI/network.
const helpers = source.slice(0, source.indexOf('\nfunction panel('));
function harness(response, error) {
  const calls = [], timers = new Set();
  const context = vm.createContext({AbortController, fetch: async (...args) => {
    calls.push(args); if(error)throw error; return response;
  }, setTimeout: (fn) => {timers.add(fn);return fn;}, clearTimeout: id => timers.delete(id)});
  vm.runInContext(helpers, context);
  return {call: () => context.api('/api/ask', {method:'POST',headers:{'X-CSRF-Token':'private-token'},body:'{}'}),calls,timers};
}
const json = (body, status=200, type='application/json') => new Response(body,{status,headers:{'Content-Type':type}});
async function rejectsSafely(response, pattern, error) {
  const h=harness(response,error);
  await assert.rejects(h.call(), e => {
    assert.match(e.message, pattern);
    assert.doesNotMatch(e.message, /DOCTYPE|private-token|secret|Unexpected token|login\.example/);
    return true;
  });
  assert.equal(h.calls.length,1,'never automatically replay a POST');
  assert.equal(h.timers.size,0,'always clear timer');
}
for(const type of ['application/json; charset=utf-8','Application/JSON','application/problem+json']) {
  test('valid object JSON '+type,async()=>{
    const h=harness(json('{"answer":"Respuesta"}',200,type));
    assert.equal((await h.call()).answer,'Respuesta');assert.equal(h.timers.size,0);
  });
}
test('blocks redirects in fetch while preserving POST and CSRF',async()=>{
  const h=harness(json('{}'));await h.call();
  const options=h.calls[0][1];assert.equal(options.redirect,'manual');assert.equal(options.method,'POST');
  assert.equal(options.headers['X-CSRF-Token'],'private-token');assert.equal(options.body,'{}');
});
for(const status of [200,502,503])test('HTML HTTP '+status,()=>rejectsSafely(new Response('<!DOCTYPE html>private-token',{status,headers:{'Content-Type':'text/html'}}),status===200?/formato esperado.*recarga/i:/HTTP 50[23].*espera/i));
for(const status of [401,403])test('HTTP access '+status,()=>rejectsSafely(json('{"detail":"secret"}',status),status===401?/sesión.*inicia sesión/i:/permisos.*administrador/i));
for(const status of [404,429,500])test('HTTP status '+status,()=>rejectsSafely(json('{"detail":"<!DOCTYPE private-token"}',status),new RegExp('HTTP '+status)));
for(const [body,type] of [['<!DOCTYPE private-token','application/json'],['','application/json'],['null','application/json'],['[]','application/json'],['"secret"','application/json'],['{}','text/plain'],['{}','']])test('invalid response '+JSON.stringify([body,type]),()=>rejectsSafely(json(body,200,type),/formato esperado.*recarga/i));
test('redirect status',()=>rejectsSafely(new Response(null,{status:302,headers:{Location:'https://login.example/?secret=1'}}),/redirigida.*sesión/i));
test('opaque redirect',()=>{const r=new Response(null);Object.defineProperty(r,'type',{value:'opaqueredirect'});return rejectsSafely(r,/redirigida.*sesión/i);});
test('already redirected response',()=>{const r=json('{}');Object.defineProperty(r,'redirected',{value:true});return rejectsSafely(r,/redirigida.*sesión/i);});
test('network failure hides raw URL',()=>rejectsSafely(null,/conectar.*conexión/i,new TypeError('secret https://login.example')));
test('timeout remains distinct',()=>rejectsSafely(null,/tiempo de espera.*seguir procesándola/i,new DOMException('secret','AbortError')));
test('aborted JSON read remains timeout',()=>{const r=json('{}');r.json=async()=>{throw new DOMException('secret','AbortError');};return rejectsSafely(r,/tiempo de espera/);});
