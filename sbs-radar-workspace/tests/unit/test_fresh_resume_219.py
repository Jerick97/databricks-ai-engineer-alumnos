from pathlib import Path
import importlib.util,shutil
import pytest
ROOT=Path(__file__).resolve().parents[2]
s=importlib.util.spec_from_file_location('resume219test',ROOT/'runs/sk06-sk11-fresh-219-resume.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
def test_actual_zero_sql_preserves_start():
 p=m.validate_zero(ROOT);assert len(p['sql'])==32
 assert m.base.read(ROOT,m.STATE+'/warehouse-start-intent-root.json')['attempt']==1

def test_sql_intent_blocks_before_prepare(tmp_path):
 target=tmp_path/m.STATE;shutil.copytree(ROOT/m.STATE,target)
 (target/'intent-01.json').write_text('{}')
 with pytest.raises(ValueError,match='STATE_PROGRESSED'):m.validate_zero(tmp_path)

def test_existing_observation_blocks_before_prepare(tmp_path):
 target=tmp_path/m.STATE;shutil.copytree(ROOT/m.STATE,target)
 (target/'observations/new.json').write_text('{}')
 with pytest.raises(ValueError,match='OBSERVATIONS_CHANGED'):m.validate_zero(tmp_path)

def test_same_bytes_reopen_journal_and_different_bytes_fail(tmp_path):
 from sbs.genie.fresh_publication_081 import Journal
 j=Journal(tmp_path/'journal',plan_sha256='a'*64);j.save('meta.json',{'v':1});j.close()
 j=Journal(tmp_path/'journal',plan_sha256='a'*64);assert j.count==0;j.save('meta.json',{'v':1})
 with pytest.raises(ValueError,match='IMMUTABLE_CONFLICT'):j.save('meta.json',{'v':2})
 j.close()

def test_marker_directory_fsync_precedes_resume():
 import ast
 tree=ast.parse((ROOT/'runs/sk06-sk11-fresh-219-resume.py').read_text())
 fn=next(x for x in tree.body if isinstance(x,ast.FunctionDef) and x.name=='resume')
 calls=[n for n in ast.walk(fn) if isinstance(n,ast.Call)]
 sync=next(n.lineno for n in calls if isinstance(n.func,ast.Attribute) and n.func.attr=='fsync' and isinstance(n.args[0],ast.Name) and n.args[0].id=='parent_fd')
 execute=next(n.lineno for n in calls if isinstance(n.func,ast.Attribute) and n.func.attr=='_execute')
 assert sync<execute
