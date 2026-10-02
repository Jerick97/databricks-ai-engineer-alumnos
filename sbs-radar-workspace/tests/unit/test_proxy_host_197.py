import importlib.util,json,shutil,tempfile,unittest
from pathlib import Path
from fastapi.testclient import TestClient
from sbs.guardrails.identity import DatabricksUserIdentity
ROOT=Path(__file__).resolve().parents[2]
BASE=ROOT/'deployment/state/experimental-materialized191/source'
OVERLAY=ROOT/'runs/sk10-proxy-host-197-overlay'
ORIGIN='https://sbs-radar-pilot-7474657121564806.aws.databricksapps.com';HOST=ORIGIN.split('://')[1]
class Service:
 mode='cloud'
 def __init__(self):self.asks=0;self.actors=[]
 def for_actor(self,actor):self.actors.append(actor['subject']);return self
 def catalog(self):return {'pairs':[{'id':'pair','provisions':[{'id':'provision'}]}]}
 def ask(self,*args):self.asks+=1;return {'status':'test_only'}

def load(root,name):
 s=importlib.util.spec_from_file_location(name,root/'src/sbs/webapp/__init__.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
class Proxy197(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.temp=tempfile.TemporaryDirectory();root=Path(cls.temp.name).resolve();shutil.copytree(BASE/'src/sbs/webapp',root/'src/sbs/webapp');shutil.copyfile(OVERLAY/'src/sbs/webapp/__init__.py',root/'src/sbs/webapp/__init__.py');cls.web=load(root,'overlay197web');cls.baseline=load(BASE,'baseline191web')
 @classmethod
 def tearDownClass(cls):cls.temp.cleanup()
 def client(self,proxy='databricks_apps',mode='cloud',web=None):
  self.service=Service();self.probes=[]
  def probe(token):self.probes.append(token);return {'id':token,'active':True}
  adapter=DatabricksUserIdentity({'principals':{key:{'role':'reader','families':['cybersecurity']} for key in ('one','two')}},probe)
  options={'identity_adapter':adapter,'public_origin':ORIGIN}
  if web is None:options['trusted_proxy']=proxy
  return TestClient((web or self.web).create_app(self.service,mode=mode,**options),base_url=ORIGIN)
 def headers(self,host=HOST,token='one'):return {'host':'127.0.0.1:8000','x-forwarded-host':host,'x-forwarded-access-token':token}
 def test_baseline_actual_failure_then_exact_proxy_host_passes(self):
  old=self.client(web=self.baseline);self.assertEqual(old.get('/api/catalog',headers=self.headers()).status_code,403)
  c=self.client();r=c.get('/api/catalog',headers=self.headers());self.assertEqual(r.status_code,200);self.assertEqual(self.service.actors,['one']);self.assertIn('Secure',r.headers['set-cookie']);self.assertEqual(self.service.asks,0)
 def test_rejects_missing_list_duplicate_and_injected_hosts_before_identity(self):
  bad=['evil.test',HOST+'.evil.test',HOST+':443',HOST+':8000','https://'+HOST,HOST+'/',HOST+'.',' '+HOST,HOST+' ',HOST+',evil.test',HOST+','+HOST,'evil@'+HOST,HOST+'\t',HOST+'\r\nx-test: yes','*',HOST.upper(),'']
  c=self.client()
  for host in bad:
   with self.subTest(host=repr(host)):self.assertEqual(c.get('/api/catalog',headers=self.headers(host)).status_code,403)
  headers=self.headers();headers.pop('x-forwarded-host');self.assertEqual(c.get('/api/catalog',headers=headers).status_code,403)
  headers=[('host','127.0.0.1:8000'),('x-forwarded-host',HOST),('x-forwarded-host',HOST),('x-forwarded-access-token','one')]
  self.assertEqual(c.get('/api/catalog',headers=headers).status_code,403);self.assertEqual(self.probes,[])
 def test_names_and_valid_host_cannot_replace_token_or_policy(self):
  c=self.client();h=self.headers();h.pop('x-forwarded-access-token');h.update({'x-forwarded-user':'one','x-forwarded-email':'trusted@example.test','x-forwarded-preferred-username':'one'})
  self.assertEqual(c.get('/api/catalog',headers=h).status_code,401)
  self.assertEqual(c.get('/api/catalog',headers=self.headers(token='revoked')).status_code,401);self.assertEqual(self.service.actors,[])
 def test_direct_and_local_modes_do_not_trust_forwarded_host(self):
  c=self.client(proxy=None);self.assertEqual(c.get('/api/catalog',headers=self.headers()).status_code,403)
  h=self.headers('evil.test');h['host']=HOST;self.assertEqual(c.get('/api/catalog',headers=h).status_code,200)
  c=self.client(proxy=None,mode='local');self.assertEqual(c.get('/api/catalog',headers={'host':'evil.test','x-forwarded-host':'localhost'}).status_code,403)
  self.assertEqual(c.get('/api/catalog',headers={'host':'localhost','x-forwarded-host':'evil.test'}).status_code,200)
  for mode,proxy in [('local','databricks_apps'),('cloud','anything'),('cloud',True)]:
   with self.subTest(mode=mode,proxy=proxy),self.assertRaises(ValueError):self.client(proxy=proxy,mode=mode)
 def test_csrf_origin_and_identity_rotation_preserved(self):
  c=self.client();h=self.headers();r=c.get('/api/catalog',headers=h);token=r.json()['csrf_token'];cookie=c.cookies.get('sbs_session');body={'pair_id':'pair','provision_id':'provision','question':'hello'}
  self.assertEqual(c.post('/api/ask',headers=h,json=body).status_code,403)
  h.update({'x-csrf-token':token,'origin':'https://evil.test'});self.assertEqual(c.post('/api/ask',headers=h,json=body).status_code,403)
  h['origin']=ORIGIN;self.assertEqual(c.post('/api/ask',headers=h,json=body).status_code,200);self.assertEqual(self.service.asks,1)
  h=self.headers(token='two');r=c.get('/api/catalog',headers=h);self.assertNotEqual(c.cookies.get('sbs_session'),cookie);self.assertNotEqual(r.json()['csrf_token'],token)
  h.update({'x-csrf-token':token,'origin':ORIGIN});self.assertEqual(c.post('/api/ask',headers=h,json=body).status_code,403);self.assertEqual(self.service.asks,1)
 def test_overlay_only_three_files_and_pins_unchanged_inputs(self):
  import hashlib
  m=json.loads((OVERLAY/'manifest.json').read_text());self.assertEqual(set(m['files_sha256']),{'src/sbs/webapp/__init__.py','app133.py','app.yaml'})
  for n,h in m['base_files_sha256'].items():self.assertEqual(hashlib.sha256((BASE/n).read_bytes()).hexdigest(),h)
  for n,h in m['files_sha256'].items():self.assertEqual(hashlib.sha256((OVERLAY/n).read_bytes()).hexdigest(),h)
  app=json.loads((OVERLAY/'app.yaml').read_text());old=json.loads((BASE/'app.yaml').read_text());self.assertEqual(app,{**old,'env':old['env']+[{'name':'SBS_TRUSTED_PROXY','value':'databricks_apps'}]})
  before=(BASE/'app133.py').read_text();after=(OVERLAY/'app133.py').read_text();self.assertEqual(after,before.replace("'public_origin':origin}","'public_origin':origin,'trusted_proxy':os.environ.get('SBS_TRUSTED_PROXY')}"))
