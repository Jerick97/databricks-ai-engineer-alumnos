"""Offline regression for the sole supported-session injection change to 081."""
from pathlib import Path
import importlib.util
from types import SimpleNamespace
import pytest

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / 'runs/sk06-sk11-fresh-081.py'
ADAPTER = ROOT / 'runs/sk06-sk11-fresh-205.py'


def load():
    assert ADAPTER.exists(), '205 adapter missing'
    spec = importlib.util.spec_from_file_location('fresh205', ADAPTER)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_only_two_signatures_and_two_config_initializers_change():
    source = BASE.read_text()
    expected = source.replace('def execute(root,review_path):',
                              'def execute(root,review_path,*,cfg=None):')
    expected = expected.replace('def reconcile(root,review_path):',
                                'def reconcile(root,review_path,*,cfg=None):')
    expected = expected.replace("    cfg=Config(profile='databricks-ai-engineer-aws')",
                                "    if cfg is None:cfg=Config(profile='databricks-ai-engineer-aws')")
    assert ADAPTER.exists(), '205 adapter missing'
    assert ADAPTER.read_text() == expected
    assert source.count("    cfg=Config(profile='databricks-ai-engineer-aws')") == 2


@pytest.mark.parametrize('operation', ['execute', 'reconcile'])
def test_injected_host_is_checked_without_cli_or_cloud(monkeypatch, operation):
    m = load()
    checks = []
    monkeypatch.setattr(m, 'check_review', lambda root, review: checks.append('review'))
    monkeypatch.setattr(m, 'prepare', lambda root: {
        'server': {'workspace_host': 'https://dbc-0410b264-20c7.cloud.databricks.com'}})
    monkeypatch.setattr(m, 'preflight', lambda root: {'connector_ready': True})
    def forbidden(*_args, **_kwargs):
        pytest.fail('injected Config must not construct a second SDK Config or transport')
    monkeypatch.setattr('databricks.sdk.core.Config', forbidden)
    class ForbiddenApi:
        def __init__(self, *_args, **_kwargs):
            forbidden()
    monkeypatch.setattr('sbs.operations.cloud_driver.SingleAttemptApi', ForbiddenApi)
    with pytest.raises(Exception, match='FRESH_HOST_MISMATCH'):
        getattr(m, operation)(ROOT, 'review-not-read.json',
                              cfg=SimpleNamespace(host='https://wrong.invalid'))
    assert checks == ['review']
