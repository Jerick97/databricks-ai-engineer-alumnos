"""SK12 evidence collector for an already authenticated real Playwright page.

Does not create credentials, issue API calls instead of UI actions, or retry a
submission. A timeout leaves its intent on disk and requires reconciliation.
"""
import json
import time
from pathlib import Path


def ask(page, case_id, question, *, cross=False, directory=Path('runs/ui225')):
    if not case_id.replace('-', '').replace('_', '').isalnum():
        raise ValueError('Invalid evidence name')
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    intent_path = directory / (case_id + '-intent.json')
    if intent_path.exists():
        raise ValueError('Existing attempt must be reconciled, not overwritten')
    page.get_by_role('button', name='03 · Chat y revisión', exact=True).click()
    page.locator('#cross').set_checked(cross)
    page.locator('#question').fill(question)
    intent = dict(question=question, cross=cross,
                  pair=page.locator('#pair').input_value(),
                  provision=page.locator('#provision').input_value(),
                  started_ms=int(time.time() * 1000))
    intent_path.write_text(json.dumps(intent, ensure_ascii=False, indent=2) + '\n')
    with page.expect_response(lambda r: r.url.endswith('/api/ask'), timeout=180000) as pending:
        page.locator('#send').click()
    response = pending.value
    body = response.json()
    (directory / (case_id + '-response.json')).write_text(
        json.dumps(body, ensure_ascii=False, indent=2) + '\n')
    page.wait_for_function('!document.getElementById("send").disabled', timeout=10000)
    (directory / (case_id + '-visible.txt')).write_text(page.locator('#messages').inner_text())
    page.locator('#messages').screenshot(path=str(directory / (case_id + '-messages.png')))
    result = dict(case=case_id, http=response.status, status=body.get('status'),
                  citations=len(body.get('citations', [])),
                  structured_results=body.get('structured_results', []),
                  elapsed_seconds=round((time.time() * 1000 - intent['started_ms']) / 1000, 2))
    (directory / (case_id + '-summary.json')).write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps(result, ensure_ascii=False))
    return body
