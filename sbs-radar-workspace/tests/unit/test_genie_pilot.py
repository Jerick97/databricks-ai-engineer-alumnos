import json
from pathlib import Path
import sqlite3
from sbs.genie import ScopedCatalog, COLUMNS, ddl

ROOT=Path(__file__).resolve().parents[2]


def test_pilot_articles_have_two_actual_rows_and_sql_matches():
    from sbs.genie.pilot import build_pilot_002
    result=build_pilot_002(ROOT)
    bundle=result['bundle'];contexts=result['contexts']
    assert len(bundle['tables']['provisions'])==141
    assert result['mapping']['raw_page_count']==135
    assert result['mapping']['structural_provision_count']==6
    assert {c['pair']['pair_id'] for c in contexts}=={'cyber-504','market-3274'}
    cat=ScopedCatalog(bundle,contexts,table_prefix=result['config']['table_prefix'])
    db=sqlite3.connect(':memory:');db.executescript(ddl(remote=False))
    db.create_function('get_json_object',2,lambda raw,key:json.loads(raw).get(key[2:]))
    for table,rows in bundle['tables'].items():
        db.executemany('INSERT INTO '+table+' VALUES ('+','.join('?' for _ in COLUMNS)+')',[[r[k] for k in COLUMNS] for r in rows])
    for context in contexts:
        plans=cat.references(context)
        assert plans['provision_count']['rows']==[['2']]
        for p in plans.values():
            actual=db.execute(p['sql'].replace(result['config']['table_prefix']+'.',''),p['parameters']).fetchall()
            assert [[str(v) for v in row] for row in actual]==p['rows']
    assert all(not row['human_approved'] for rows in bundle['tables'].values() for row in rows)
    assert build_pilot_002(ROOT)==result


def test_pilot_export_roundtrip(tmp_path):
    from sbs.genie.pilot import export_pilot_002
    result=export_pilot_002(ROOT,tmp_path/'bundle',tmp_path/'config.json')
    manifest=json.loads((tmp_path/'bundle/manifest.json').read_text())
    manifest['tables']={t:[json.loads(line) for line in (tmp_path/'bundle'/f'{t}.jsonl').read_text().splitlines()] for t in result['bundle']['tables']}
    ScopedCatalog(manifest,result['contexts'],table_prefix=result['config']['table_prefix'])
    assert json.loads((tmp_path/'config.json').read_text())['snapshot']==manifest['snapshot_hash']
    assert len(json.loads((tmp_path/'bundle/benchmark-questions.json').read_text()))==5


def test_pilot_relocated_and_tampered_source_rejected(tmp_path,monkeypatch):
    import shutil
    import pytest
    from sbs.genie.pilot import build_pilot_002
    expected=build_pilot_002(ROOT)
    for name in expected['mapping']['input_files']:
        target=tmp_path/name;target.parent.mkdir(parents=True,exist_ok=True)
        shutil.copyfile(ROOT/name,target)
    original=Path.open
    def guarded(path,*args,**kwargs):
        assert not any(path.resolve().is_relative_to(ROOT/d) for d in ('runs','data','context')), 'original corpus read'
        return original(path,*args,**kwargs)
    monkeypatch.setattr(Path,'open',guarded)
    assert build_pilot_002(tmp_path)==expected
    capture=json.loads((tmp_path/'runs/sk02-repository-capture.json').read_text())
    from sbs.paths import project_path
    project_path(tmp_path,capture['sources'][0]['rawtext_path']).write_text('tampered')
    with pytest.raises(ValueError,match='SOURCE_BYTES'):build_pilot_002(tmp_path)
