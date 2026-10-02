"""Bounded registered-source capture; discovery produces candidates, never law."""
from html.parser import HTMLParser
from urllib.parse import urljoin,urlsplit
from copy import deepcopy
import re,unicodedata
from . import sha,canonical,RefreshRunner
from .preparers import build_real_hooks
from sbs.foundation.transport import fetch_pdf
from sbs.guardrails import check_source_url

INDEX_URLS=frozenset({'https://www.sbs.gob.pe/autorizacion-de-nuevas-empresas/marco-normativo-y-documentos-de-apoyo','https://www.sbs.gob.pe/app/pp/INT_CN/Paginas/Busqueda/VerHistorial.aspx?NormaId=1731'})

def observed_pairs(before,after):
    old={x['source_key']:x for x in before if not x.get('retained')};pairs=[];provenance=[]
    for new in after:
        prior=old.get(new['source_key'])
        if prior is None or prior['sha256']==new['sha256']:continue
        if any(prior[k]!=new[k] for k in ('document_id','family')):raise ValueError('SOURCE_IDENTITY_CHANGED')
        pair={'pair_id':'observed-'+sha(canonical([new['source_key'],prior['sha256'],new['sha256']])),'family':new['family'],'before':{'document_id':prior['document_id'],'version_id':prior['sha256']},'after':{'document_id':new['document_id'],'version_id':new['sha256']}}
        pairs.append(pair);provenance.append({'pair_id':pair['pair_id'],'source_key':new['source_key'],'basis':'same_registered_url_observed_bytes_change','legal_effect_established':False})
    return pairs,provenance


def transform_capture(sources,previous,pairs,*,previous_pairs=(),previous_provenance=()):
    added,provenance=observed_pairs(previous,sources)
    # The verified prior release is a catalog, not merely the last GET delta.
    # Retain observed history and its explicit non-legal provenance across runs.
    by_id={p['pair_id']:p for p in previous_pairs};carried=[];carried_provenance=[]
    for item in previous_provenance:
        pair=by_id.get(item['pair_id'])
        if pair is None:raise ValueError('OBSERVED_PAIR_HISTORY_INVALID')
        endpoints=[]
        for side in ('before','after'):
            matches=[x for x in previous if x['source_key']==item['source_key'] and x['document_id']==pair[side]['document_id'] and x['sha256']==pair[side]['version_id'] and x['family']==pair['family']]
            if len(matches)!=1:raise ValueError('OBSERVED_PAIR_HISTORY_INVALID')
            endpoints.append(matches[0])
        expected,origin=observed_pairs([{**endpoints[0],'retained':False}],[endpoints[1]])
        if expected!=[pair] or origin!=[item]:raise ValueError('OBSERVED_PAIR_HISTORY_INVALID')
        carried.append(deepcopy(pair));carried_provenance.append(deepcopy(item))
    combined=deepcopy(list(pairs))
    for pair in carried+added:
        same=[p for p in combined if p['pair_id']==pair['pair_id']]
        if same and same!=[pair]:raise ValueError('OBSERVED_PAIR_HISTORY_INVALID')
        if not same:combined.append(pair)
    provenance=carried_provenance+[p for p in provenance if p not in carried_provenance]
    needed={(p[side]['document_id'],p[side]['version_id']) for p in combined for side in ('before','after')}
    current={(x['document_id'],x['sha256']) for x in sources};retained=[]
    for old in previous:
        key=(old['document_id'],old['sha256'])
        if key in needed and key not in current:
            retained.append({**old,'retained':True,'fresh_remote_capture':False});current.add(key)
    return sources+retained,tuple(combined),provenance


def registered_fetcher(plan,transport=fetch_pdf):
    entries={s['url']:s for s in plan.manifest['sources']}
    def fetch(url,*,allowed_hosts):
        if url not in entries:raise ValueError('SOURCE_NOT_WHITELISTED')
        raw,final=transport(url,allowed_hosts=allowed_hosts)
        # Redirects may not silently move the document identity to another URL.
        if final!=url:raise ValueError('REGISTERED_SOURCE_REDIRECT_CHANGED')
        if sha(raw)!=plan.hashes[url]:
            from sbs.foundation.pdf_reader import strict_pdf_reader
            text=strict_pdf_reader(raw).pages[0].extract_text() or ''
            text=''.join(c for c in unicodedata.normalize('NFKD',text.casefold()) if not unicodedata.combining(c))
            match=re.search(r'resolucion\s+s[.]?\s*b[.]?\s*s[.]?\s*(?:n[^0-9]{0,5})?\s*0*([0-9]+)\s*[-–]\s*([0-9]{4})',text[:1000])
            expected=re.fullmatch(r'sbs-0*([0-9]+)-([0-9]{4})',entries[url]['document_id'])
            if not match or not expected or (int(match[1]),match[2])!=(int(expected[1]),expected[2]):raise ValueError('DOCUMENT_TITLE_IDENTITY_NOT_VERIFIED')
        return raw,final
    fetch.capture_evidence_mode='real' if transport is fetch_pdf else 'injected_adapter'
    return fetch


def run_refresh(project,plan,state_root,*,run_id,capture_mode='sealed',fetcher=None,fail_at=None,annotations=()):
    if capture_mode not in ('sealed','remote'):raise ValueError('CAPTURE_MODE_INVALID')
    runner=RefreshRunner(plan,state_root)
    if capture_mode=='remote':
        # Immutable previous versions copied from trusted sealed originals. These
        # are explicitly local baseline, not a new remote observation.
        runner.bootstrap_capture()
    return runner.run(run_id=run_id,hooks=build_real_hooks(project,annotations=annotations),fetcher=registered_fetcher(plan,fetcher or fetch_pdf) if capture_mode=='remote' else None,force_revalidate=True,fail_at=fail_at,capture_transform=transform_capture if capture_mode=='remote' else None)


class Links(HTMLParser):
    def __init__(self):super().__init__();self.links=[];self.href=None;self.parts=[]
    def handle_starttag(self,tag,attrs):
        if tag=='a':self.href=dict(attrs).get('href');self.parts=[]
    def handle_data(self,data):
        if self.href is not None:self.parts.append(data)
    def handle_endtag(self,tag):
        if tag=='a' and self.href is not None:
            if len(self.links)>=500:raise ValueError('DISCOVERY_LINK_CAP')
            self.links.append((self.href,' '.join(self.parts)[:1000]));self.href=None


def discover_candidates(raw,*,index_url,observed_at):
    if index_url not in INDEX_URLS or not isinstance(raw,bytes) or len(raw)>1024*1024:raise ValueError('DISCOVERY_INPUT_DENIED')
    parser=Links();parser.feed(raw.decode('utf-8',errors='replace'));candidates=[];seen=set()
    for href,title in parser.links:
        url=urljoin(index_url,href)
        if url in seen or not check_source_url(url,['www.sbs.gob.pe','intranet2.sbs.gob.pe'])['valid'] or not urlsplit(url).path.lower().endswith('.pdf'):continue
        seen.add(url);text=''.join(c for c in unicodedata.normalize('NFKD',title.casefold()) if not unicodedata.combining(c))
        family='cybersecurity' if any(t in text for t in ('ciberseguridad','seguridad de la informacion')) else 'market_conduct' if 'conducta de mercado' in text else None
        sector='insurance' if any(t in text for t in ('seguros','asegurador')) else 'banking' if any(t in text for t in ('banco','sistema financiero','empresas financieras')) else 'unknown'
        eligibility='potential_bank_candidate_requires_review' if family and sector=='banking' else 'excluded_sector_mismatch' if sector=='insurance' else 'pending_family_or_sector'
        candidates.append({'url':url,'anchor_text':title,'family_hint':family,'sector_hint':sector,'eligibility':eligibility,'status':'candidate_only','auto_include':False,'provenance':{'index_url':index_url,'index_sha256':sha(raw),'observed_at':observed_at},'legal_effect_established':False})
    return {'candidates':candidates,'index_sha256':sha(raw),'coverage':'bounded_links_not_complete_inventory','automatic_ingestion':False}


def discover_remote(index_url,*,observed_at):
    if index_url not in INDEX_URLS:raise ValueError('DISCOVERY_INDEX_DENIED')
    # Existing pinned TLS/DNS/deadline transport; PDF validation is performed by
    # ingest, not fetch_pdf. Discovery accepts bounded HTML only after download.
    raw,final=fetch_pdf(index_url,allowed_hosts=['www.sbs.gob.pe','intranet2.sbs.gob.pe'])
    if final!=index_url:raise ValueError('DISCOVERY_INDEX_REDIRECT_UNEXPECTED')
    return discover_candidates(raw,index_url=index_url,observed_at=observed_at)
