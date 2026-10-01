"""SK11 incremental capture releases, local POSIX state, no scheduler activation.

No import causes I/O. Network GET is opt-in via trusted fetcher; default reuses
sealed PDFs. Hooks prepare local artifacts, never mutate published services.
"""
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime,timezone
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import secrets
import stat
import time
from sbs.foundation import ingest,extract
from sbs.paths import project_path
from sbs.foundation.transport import MAX_BYTES


def sha(raw):return hashlib.sha256(raw).hexdigest()
def canonical(value):return json.dumps(value,sort_keys=True,ensure_ascii=False,separators=(',',':')).encode()
def now():return datetime.now(timezone.utc).isoformat()


def _reject_symlinks(root):
    root=Path(root)
    if root.is_symlink():raise ValueError('STATE_PATH_SYMLINK')
    if root.exists() and any(p.is_symlink() for p in root.rglob('*')):
        raise ValueError('STATE_PATH_SYMLINK')


def _directory_fd(path):
    """Traverse/create owned directories using no-follow directory descriptors."""
    path=Path(path).absolute();fd=os.open(path.anchor,os.O_RDONLY|os.O_DIRECTORY)
    try:
        for part in path.parts[1:]:
            try:os.mkdir(part,dir_fd=fd)
            except FileExistsError:pass
            try:new=os.open(part,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW,dir_fd=fd)
            except OSError:raise ValueError('STATE_PATH_INVALID') from None
            os.close(fd);fd=new
        return fd
    except BaseException:
        os.close(fd);raise


def _reject_link_at(fd,name):
    try:mode=os.stat(name,dir_fd=fd,follow_symlinks=False).st_mode
    except FileNotFoundError:return
    if stat.S_ISLNK(mode):raise ValueError('STATE_PATH_SYMLINK')


def atomic(path,value):
    path=Path(path);directory=_directory_fd(path.parent);name='.pending-'+secrets.token_hex(16)
    try:
        _reject_link_at(directory,path.name)
        fd=os.open(name,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600,dir_fd=directory)
        with os.fdopen(fd,'wb') as f:f.write(canonical(value));f.flush();os.fsync(f.fileno())
        _reject_link_at(directory,path.name)
        os.replace(name,path.name,src_dir_fd=directory,dst_dir_fd=directory)
        os.fsync(directory)
    finally:
        try:os.unlink(name,dir_fd=directory)
        except FileNotFoundError:pass
        os.close(directory)


@contextmanager
def exclusive_lock(root):
    root=Path(root);_reject_symlinks(root);directory=_directory_fd(root)
    try:
        _reject_link_at(directory,'.refresh.lock')
        fd=os.open('.refresh.lock',os.O_WRONLY|os.O_CREAT|os.O_NOFOLLOW,0o600,dir_fd=directory)
    finally:os.close(directory)
    with os.fdopen(fd,'a') as f:
        try:fcntl.flock(f,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError:raise RuntimeError('LOCK_BUSY') from None
        try:
            _reject_symlinks(root)
            yield
        finally:fcntl.flock(f,fcntl.LOCK_UN)


@dataclass(frozen=True)
class SealedPlan:
    manifest:dict
    originals:dict
    hashes:dict
    identity:str
    pairs:tuple=()


def plan_fingerprint(plan):return sha(canonical({'manifest':plan.manifest,'pairs':plan.pairs}))


PENDING_REASONS=frozenset({'EMBEDDINGS_MISSING','TOKENIZER_PENDING','INFERENCE_QUOTA_EXCEEDED','PAIRS_PENDING','PAIR_SOURCE_MISSING','ANNOTATION_SOURCE_CHANGED','UPSTREAM_PENDING'})


def verify_closure(root,closure):
    if not isinstance(closure,dict) or len(closure)>2000:raise ValueError('PREPARED_CLOSURE_INTEGRITY')
    root=Path(root).resolve()
    for name,expected in closure.items():
        if not isinstance(name,str) or Path(name).is_absolute() or '..' in Path(name).parts or not Path(name).parts or not isinstance(expected,str) or not re.fullmatch('[0-9a-f]{64}',expected):raise ValueError('PREPARED_CLOSURE_INTEGRITY')
        target=root/name
        if any(p.is_symlink() for p in (target,*target.parents) if p!=root and p.is_relative_to(root)) or not target.resolve().is_relative_to(root):raise ValueError('PREPARED_CLOSURE_INTEGRITY')
        try:actual=sha(target.read_bytes())
        except OSError:raise ValueError('PREPARED_CLOSURE_INTEGRITY') from None
        if actual!=expected:raise ValueError('PREPARED_CLOSURE_INTEGRITY')


def load_sealed_plan(project):
    """Read only two existing capture manifests; exact source URL whitelist."""
    project=Path(project).resolve();entries=[];originals={};hashes={};hosts=set()
    for name in ('sk02-repository-capture.json','sk02-amendments-capture.json'):
        capture=json.loads((project/'runs'/name).read_text())
        manifest_path=project_path(project,capture['manifest']);raw=manifest_path.read_bytes()
        if sha(raw)!=capture['manifest_sha256']:raise ValueError('MANIFEST_INTEGRITY')
        manifest=json.loads(raw);hosts.update(manifest['allowed_hosts'])
        lookup={(x['document_id'],x['url']):x for x in manifest['sources']}
        for entry in capture['sources']:
            source=entry['source'];key=(source['document_id'],source['url'])
            if key not in lookup:raise ValueError('SOURCE_NOT_WHITELISTED')
            p=project_path(project,entry['original_path'])
            if not p.is_relative_to(project):raise ValueError('ORIGINAL_OUTSIDE_PROJECT')
            if sha(p.read_bytes())!=source['sha256']:raise ValueError('ORIGINAL_INTEGRITY')
            if source['url'] in originals:raise ValueError('DUPLICATE_SOURCE')
            entries.append(lookup[key]);originals[source['url']]=p;hashes[source['url']]=source['sha256']
    manifest={'allowed_hosts':sorted(hosts),'sources':entries}
    return SealedPlan(manifest,originals,hashes,sha(canonical(manifest)))


class RefreshRunner:
    def __init__(self,plan,state_root,*,max_sources=6,max_total_bytes=120*1024*1024,max_seconds=300):
        if any(type(n) is not int or n<=0 for n in (max_sources,max_total_bytes,max_seconds)):raise ValueError('INVALID_CAP')
        if len(plan.manifest['sources'])>max_sources:raise ValueError('SOURCE_CAP')
        if Path(state_root).is_symlink():raise ValueError('STATE_PATH_SYMLINK')
        self.plan=plan;self.root=Path(state_root).resolve();self.max_bytes=max_total_bytes;self.max_seconds=max_seconds
        if any(p.is_relative_to(self.root) for p in plan.originals.values()):raise ValueError('STATE_OVERLAPS_ORIGINALS')

    def current(self):
        p=self.root/'current.json'
        if p.is_symlink():raise ValueError('RELEASE_POINTER_SYMLINK')
        if not p.exists():return None
        try:
            pointer=json.loads(p.read_text())
        except (ValueError,UnicodeError):
            raise ValueError('RELEASE_POINTER_INVALID') from None
        if (not isinstance(pointer,dict) or set(pointer)!={'release_id','sha256'} or
            any(not isinstance(pointer.get(k),str) or not re.fullmatch(r'[0-9a-f]{64}',pointer[k]) for k in ('release_id','sha256'))):
            raise ValueError('RELEASE_POINTER_INVALID')
        release=self.root/'releases'/pointer['release_id']/'release.json'
        if any(part.is_symlink() for part in (release,*release.parents) if part!=self.root and part.is_relative_to(self.root)):
            raise ValueError('RELEASE_POINTER_INVALID')
        try:verify_closure(self.root,{str(release.relative_to(self.root)):pointer['sha256']})
        except ValueError:raise ValueError('RELEASE_INTEGRITY') from None
        data=json.loads(release.read_text())
        for item in data.get('prepared',{}).values():
            try:verify_closure(self.root,{item['artifact_path']:item['sha256']})
            except ValueError:raise ValueError('PREPARED_ARTIFACT_INTEGRITY') from None
            verify_closure(self.root,item.get('closure',{}))
        return pointer

    def _release(self):
        p=self.current()
        return json.loads((self.root/'releases'/p['release_id']/'release.json').read_text()) if p else None

    def _capture(self,run_id,fetcher=None,budget=None):
        budget=budget if budget is not None else {'bytes':0,'requests':0};start=time.monotonic()
        def bounded(url,*,allowed_hosts):
            if url not in self.plan.originals:raise ValueError('SOURCE_NOT_WHITELISTED')
            if time.monotonic()-start>self.max_seconds:raise ValueError('TIME_CAP')
            if fetcher is None:
                content=self.plan.originals[url].read_bytes();final=url
                if sha(content)!=self.plan.hashes[url]:raise ValueError('SEALED_BYTES_CHANGED')
            else:
                if budget['bytes']+MAX_BYTES>self.max_bytes:raise ValueError('BYTE_CAP')
                budget['requests']+=1;content,final=fetcher(url,allowed_hosts=allowed_hosts)
            budget['bytes']+=len(content)
            if len(content)>MAX_BYTES or budget['bytes']>self.max_bytes:raise ValueError('BYTE_CAP')
            return content,final
        captured=ingest(self.plan.manifest,run_id,root=self.root/'foundation',fetcher=bounded)
        if len(captured)!=len(self.plan.manifest['sources']):raise ValueError('CAPTURE_INCOMPLETE')
        sources=[]
        for index,source in enumerate(captured):
            if time.monotonic()-start>self.max_seconds:raise ValueError('TIME_CAP')
            bundle=extract(source,root=self.root/'foundation')
            sources.append({'source_id':'source-'+str(index+1),'source_key':sha(canonical([source['document_id'],source['url']])),'document_id':source['document_id'],'family':source['family'],
                            'sha256':source['sha256'],'rawtext_sha256':bundle['rawtext_sha256'],
                            'extraction_config_hash':bundle['config_hash'],'extractor':bundle['extractor'],
                            'quality':bundle['quality']['status']})
        return sources,budget

    def _publish(self,release):
        for item in release.get('prepared',{}).values():
            verify_closure(self.root,{**item.get('closure',{}),item['artifact_path']:item['sha256']})
        release_id=sha(canonical(release));path=self.root/'releases'/release_id/'release.json'
        if path.exists() and path.read_bytes()!=canonical(release):raise ValueError('RELEASE_COLLISION')
        if not path.exists():atomic(path,release)
        pointer={'release_id':release_id,'sha256':sha(path.read_bytes())}
        atomic(self.root/'current.json',pointer)
        return pointer

    def bootstrap_capture(self):
        """Seed an isolated capture-only baseline; not a completed runtime release."""
        with exclusive_lock(self.root):
            if self.current():return self._release()
            sources,_=self._capture('bootstrap-capture')
            release={'release_scope':'capture_only','sources':sources,'plan_id':self.plan.identity,'plan_fingerprint':plan_fingerprint(self.plan),
                     'production_validated':False,'limitations':['downstream_validation_pending','not_current_law']}
            self._publish(release)
            return release

    def run(self,*,run_id,hooks=None,fetcher=None,force_revalidate=False,fail_at=None,capture_transform=None):
        """Finite local transaction. Same run_id returns its recorded terminal result.

        hooks SK03/SK04/SK06(context) prepare local validated artifacts; validation
        is a backend assertion, not automatic legal approval. Missing hooks block
        promotion. Network mode requires explicit fetch_pdf passed by backend.
        """
        if not isinstance(run_id,str) or not re.fullmatch(r'[A-Za-z0-9_-]{1,80}',run_id):raise ValueError('INVALID_RUN_ID')
        hooks=hooks or {}
        if not set(hooks)<= {'SK03','SK04','SK06'}:raise ValueError('UNKNOWN_HOOK')
        with exclusive_lock(self.root):
            path=self.root/'runs'/run_id/'result.json'
            if path.exists():
                recorded=json.loads(path.read_text())
                if recorded.get('mode')!=('reuse_sealed' if fetcher is None else 'trusted_get_adapter'):raise ValueError('RUN_CAPTURE_MODE_CONFLICT')
                if recorded.get('plan_id')!=self.plan.identity or recorded.get('plan_fingerprint')!=plan_fingerprint(self.plan):raise ValueError('RUN_PLAN_CONFLICT')
                return recorded
            started=now();previous=self.current();release=self._release();stage=self.root/'runs'/run_id/'stage';os.close(_directory_fd(stage))
            result={'run_id':run_id,'plan_id':self.plan.identity,'plan_fingerprint':plan_fingerprint(self.plan),'publication_committed':False,'real_preparation_completed':False,'e2e_acceptance':'not_evaluated','started_at':started,'status':'started','previous':previous,'current':previous,
                    'cost':None,'cost_state':'unknown','network_requests':0,'production_validated':False,
                    'mode':'reuse_sealed' if fetcher is None else 'trusted_get_adapter','capture_evidence_mode':getattr(fetcher,'capture_evidence_mode','unverified_adapter') if fetcher else 'sealed_reuse','changed_sources':[],'pending_hooks':{},
                    'limitations':['Byte freshness is not legal validity or proof of no legal modifications.'],'error_code':None}
            atomic(self.root/'runs'/run_id/'started.json',result)
            changes=[];budget={'bytes':0,'requests':0};expected_commit=None
            try:
                sources,budget=self._capture(run_id,fetcher,budget);result['fetch_attempts']=budget['requests'];result['network_requests']=0 if budget['requests']==0 else None;result['bytes_observed']=budget['bytes']
                # Stable source identity plus full captured metadata; membership and
                # plan transitions invalidate preparation even when PDF bytes match.
                identity=lambda s:s.get('source_key') or sha(canonical([s['document_id'],s['source_id']]))
                before={identity(s):s for s in release['sources'] if not s.get('retained')} if release else {}
                after={identity(s):s for s in sources}
                if len(after)!=len(sources):raise ValueError('DUPLICATE_SOURCE_KEY')
                plan_changed=bool(release and (release.get('plan_id')!=self.plan.identity or release.get('plan_fingerprint')!=plan_fingerprint(self.plan)))
                removed=[s for key,s in before.items() if key not in after]
                changes=[s for s in sources if force_revalidate or plan_changed or before.get(identity(s))!=s]
                result['plan_changed']=plan_changed
                result['removed_sources']=[s['source_id'] for s in removed]
                result['changed_sources']=[s['source_id'] for s in changes]
                if fetcher is not None:
                    atomic(self.root/'last_capture_success.json',{'run_id':run_id,'verified_at':now(),'mode':'remote','evidence_mode':result['capture_evidence_mode'],'source_hashes':{x['source_key']:x['sha256'] for x in sources},'legal_changes':'not_assessed','fetch_attempts':budget['requests']})
                effective_pairs=self.plan.pairs
                if capture_transform is not None:
                    prior_pairs=[]
                    if release and 'SK03' in release.get('prepared',{}):
                        prior_item=release['prepared']['SK03']
                        prior_pairs=json.loads((self.root/prior_item['artifact_path']).read_bytes())['payload']['pairs']
                    sources,effective_pairs,pair_provenance=capture_transform(sources,release['sources'] if release else [],self.plan.pairs,previous_pairs=prior_pairs,previous_provenance=release.get('observed_pair_provenance',[]) if release else [])
                    result['observed_pair_provenance']=pair_provenance
                if not changes and not removed and not plan_changed:result['status']='unchanged_bytes'
                else:
                    backlog={'items':[{'source_id':s['source_id'],'sha256':s['sha256'],'pending':['SK03','SK04','SK06']} for s in changes],
                             'removed_sources':result['removed_sources'],'plan_changed':plan_changed,'run_id':run_id}
                    atomic(self.root/'backlog.json',backlog)
                    prepared={}
                    for key in ('SK03','SK04','SK06'):
                        if key not in hooks:continue
                        output=hooks[key]({'hook':key,'run_id':run_id,'plan_id':self.plan.identity,'plan_fingerprint':plan_fingerprint(self.plan),'pairs':effective_pairs,'state_root':self.root,'stage':stage,'changed_sources':changes,'removed_sources':removed,'sources':sources,'plan_changed':plan_changed,'previous_release':release,'foundation_root':self.root/'foundation'})
                        if isinstance(output,dict) and output.get('status')=='pending':
                            if output.get('reason') not in PENDING_REASONS:raise ValueError('HOOK_VALIDATION_FAILED')
                            result['pending_hooks'][key]=output['reason'];continue
                        if not isinstance(output,dict) or output.get('status')!='validated' or output.get('mode') not in ('real','fixture'):raise ValueError('HOOK_VALIDATION_FAILED')
                        artifact=(stage/output['artifact_path']).resolve()
                        if not artifact.is_relative_to(stage.resolve()) or sha(artifact.read_bytes())!=output['sha256']:raise ValueError('HOOK_ARTIFACT_INVALID')
                        closure=output.get('closure',{});verify_closure(self.root,closure)
                        prepared[key]={'artifact_path':str(artifact.relative_to(self.root)),'sha256':output['sha256'],'mode':output['mode'],'closure':closure}
                    if len(prepared)!=3:result['status']='pending_validation'
                    else:
                        if fail_at=='before_publish':raise ValueError('INJECTED_FAILURE')
                        candidate={'release_scope':'prepared_downstream','sources':sources,'plan_id':self.plan.identity,'plan_fingerprint':plan_fingerprint(self.plan),'prepared':prepared,
                                   'production_validated':False,'real_preparation_completed':all(x['mode']=='real' for x in prepared.values()),'e2e_acceptance':'not_evaluated','limitations':['not_current_law','semantic_validation_external']}
                        if capture_transform is not None:candidate.update(capture_evidence_mode=result['capture_evidence_mode'],observed_pair_provenance=result.get('observed_pair_provenance',[]))
                        expected_commit={'release_id':sha(canonical(candidate)),'sha256':sha(canonical(candidate))}
                        result['current']=self._publish(candidate);result['publication_committed']=True;result['real_preparation_completed']=candidate['real_preparation_completed'];result['status']='published'
                        atomic(self.root/'backlog.json',{'items':[],'run_id':run_id})
            except Exception as exc:
                if expected_commit is not None and self.current()==expected_commit:
                    result['publication_committed']=True
                    result['real_preparation_completed']=candidate['real_preparation_completed']
                result['status']='published_cleanup_pending' if result['publication_committed'] else 'failed'
                code=str(exc) if isinstance(exc,ValueError) else ''
                result['error_code']='POST_COMMIT_CLEANUP_FAILED' if result['publication_committed'] else code if code in {'CAPTURE_INCOMPLETE','TIME_CAP','HOOK_VALIDATION_FAILED','HOOK_ARTIFACT_INVALID','INJECTED_FAILURE'} else 'REFRESH_FAILED'
            result['fetch_attempts']=budget['requests'];result['network_requests']=0 if budget['requests']==0 else None;result['bytes_observed']=budget['bytes']
            result['ended_at']=now();result['current']=self.current()
            atomic(path,result);atomic(self.root/'last_attempt.json',result)
            if result['status'] in ('published','published_cleanup_pending','unchanged_bytes'):
                atomic(self.root/'last_success.json',{'run_id':run_id,'verified_at':result['ended_at'],'mode':result['mode'],'network_freshness_established':result['capture_evidence_mode']=='real'})
            return result
