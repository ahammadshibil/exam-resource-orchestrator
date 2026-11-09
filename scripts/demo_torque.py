"""Generate a key-free demo from real engines and explicitly synthetic learner evidence."""
import html
import json
import subprocess
import sys
from dataclasses import asdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from exam_resources import Learner, Orchestrator, ResourceMetadataStore


def run():
    app = ROOT / 'learnharness'
    tsx = app / 'node_modules/tsx/dist/cli.mjs'
    if not tsx.exists():
        raise SystemExit('Install app dependencies first: cd learnharness && npm ci')
    code = "import {createLearningResourceSearch} from './src/server/learning-resources.ts'; createLearningResourceSearch()({query:'torque',providers:['openstax'],limit:1}).then(r=>console.log(JSON.stringify(r)))"
    referral = json.loads(subprocess.check_output(['node', str(tsx), '-e', code], cwd=app, text=True))
    assert referral['references'] and not referral['contentDownloaded'] and not referral['masteryUpdated']
    source = referral['references'][0]
    assert source['provider'] == 'openstax' and source['url'].startswith('https://openstax.org/')
    assert source['activity'] and source['followUp'] and source['accessNote']
    store = ResourceMetadataStore(':memory:')
    try:
        engine = Orchestrator(store)
        learner = Learner('synthetic-torque-demo', 'JEE', online=False)
        response = 'The perpendicular 4 N force at 0.5 m gives 2 N m. A larger force must turn it more, even if it points through the pivot.'
        gap = engine.diagnose('torque', response, [False, False, True])
        started = engine.start(learner, gap)
        assert started['status'] == 'started'
        identifier = started['intervention']
        assessment = started['prescription']['assessment']
        assert 'answer' not in assessment
        engine.tracker.record(identifier, 'completed')
        before = store.get_mastery(learner.id, 'torque')
        assert before is None, 'Completion must not establish mastery'
        # A simulated assessor supplies these marks. No learner or model was tested.
        spec = next(x for x in engine.topics['torque']['assessments'] if x['id'] == assessment['id'])
        outcome = engine.evaluator.evaluate(identifier, assessment['id'], [True] * len(spec['rubric']),
            spec['answer'], independent=True, assessor='tutor')
        after = store.get_mastery(learner.id, 'torque')
        assert after['status'] == 'demonstrated_once' and not outcome['causal_attribution']
        report = dict(synthetic=True, modelInvoked=False, liveSearch=False,
            diagnostic=dict(prompt=engine.diagnostic('torque')['prompt'], response=response,
                marks=[False, False, True], gap=asdict(gap)),
            resourceTool=referral, assessment=dict(prompt=assessment['prompt'],
                syntheticResponse=spec['answer'], suppliedMarks=[True] * len(spec['rubric']),
                masteryAfterCompletion=before, score=outcome['score'], status=after['status'],
                causalAttribution=outcome['causal_attribution']),
            boundary='Native TypeScript catalog and standalone Python assessment run separately. This does not synchronize LearnHarness sessions or graph with Python history.')
    finally:
        store.close()
    dest = ROOT / 'docs/demo'
    dest.mkdir(exist_ok=True)
    (dest / 'torque.json').write_text(json.dumps(report, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    e = html.escape
    steps = [
        ('Find the gap', 'A bigger force does not always turn more.',
         '<label>DIAGNOSTIC PROMPT</label><p>' + e(report['diagnostic']['prompt']) + '</p><label>SYNTHETIC LEARNER RESPONSE</label><blockquote>' + e(response) + '</blockquote><label>ENGINE RESULT</label><p>Gap: <strong>' + e(gap.kind) + '</strong> · Baseline: 1 / 3 supplied criteria</p>'),
        ('Find a source', source['title'],
         '<label>REAL CATALOG RESULT · OPENSTAX</label><p><a href="' + e(source['url'], quote=True) + '">' + e(source['url']) + '</a></p><label>ACTIVE STUDY TASK</label><p>' + e(source['activity']) + '</p><label>ACCESS NOTE</label><p>' + e(source['accessNote']) + '</p><div class="tags"><span>No content downloaded</span><span>No mastery updated</span></div>'),
        ('Check fresh work', 'Completion alone leaves mastery unset.',
         '<label>ASSIGNED FOLLOW-UP · PYTHON ENGINE</label><p>' + e(assessment['prompt']) + '</p><details><summary>Reveal synthetic response and supplied rubric score</summary><p>' + e(spec['answer']) + '</p><p>Fixture marks: 3 / 3 → demonstrated_once. This is simulated assessment evidence, not a real learner result.</p></details><label>VERIFIED BOUNDARY</label><p>After completion: <strong>null</strong>. Only the simulated independent assessment writes a score. No causal learning claim.</p>')]
    cards = ''.join('<section id="step-' + str(i+1) + '"' + ('' if i == 0 else ' hidden') + '><div class="eyebrow">STEP 0' + str(i+1) + ' / 03 · ' + e(title.upper()) + '</div><h2>' + e(head) + '</h2>' + body + '</section>' for i, (title, head, body) in enumerate(steps))
    buttons = ''.join('<button data-step="' + str(i+1) + '" aria-pressed="' + ('true' if i == 0 else 'false') + '">0' + str(i+1) + ' · ' + e(title) + '</button>' for i, (title, _, _) in enumerate(steps))
    page = '''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Torque walkthrough · Exam Resource Orchestrator</title><style>
*{box-sizing:border-box}body{margin:0;background:#0c1421;color:#e5edf7;font:18px/1.6 system-ui,sans-serif}main{max-width:1120px;margin:36px auto;padding:0 32px}header{display:flex;align-items:center;justify-content:space-between;gap:20px}header strong{font-size:16px}small,.eyebrow,label{color:#82d8c1;font-size:12px;font-weight:700;letter-spacing:1.5px}h1{font-size:42px;line-height:1.2;margin:30px 0 12px}h2{font-size:30px;line-height:1.3;margin:12px 0 24px}.intro{color:#abbcd0;max-width:880px}.notice{background:#202c3b;border:1px solid #40516a;color:#d3deeb;padding:12px 18px;border-radius:10px;font-size:14px}nav{display:flex;gap:12px;margin:24px 0}button{cursor:pointer;border:1px solid #37475b;background:#162133;color:#c3d1e4;border-radius:8px;padding:12px 20px;font:inherit;font-size:15px}button[aria-pressed=true]{background:#85e1c3;color:#0c2424;border-color:#85e1c3}section{background:#131f30;border:1px solid #304158;border-radius:16px;padding:28px 32px;min-height:430px}p{margin:10px 0 20px}blockquote{border-left:3px solid #85e1c3;padding:10px 20px;margin:12px 0 24px;background:#1b2a3c}a{color:#8bdcfa;overflow-wrap:anywhere}.tags{display:flex;gap:10px}.tags span{padding:6px 12px;border-radius:30px;background:#203d3b;color:#9fe5cb;font-size:13px}details{margin:16px 0 24px}summary{cursor:pointer;color:#8bdcfa}footer{font-size:12px;color:#92a5bd;margin-top:20px}@media(max-width:650px){main{padding:0 18px}h1{font-size:30px}nav{flex-wrap:wrap}section{padding:22px;min-height:0}header{display:block}}
</style><main><header><strong>EXAM RESOURCE ORCHESTRATOR</strong><small>REPRODUCIBLE TORQUE DEMO</small></header><h1>From a misconception to a fresh attempt.</h1><p class="intro">Actual catalog discovery and assessment-engine output, with every boundary visible.</p><div class="notice">Documentation demo · Synthetic learner and rubric marks · No AI model invoked · Not the tutoring app interface</div><nav aria-label="Walkthrough steps">''' + buttons + '</nav>' + cards + '''<footer>Generated by scripts/demo_torque.py · TypeScript resource adapter + separate Python assessment engine · <a href="torque.json">Raw output</a></footer></main><script>
for(const button of document.querySelectorAll('button[data-step]'))button.addEventListener('click',()=>{for(const section of document.querySelectorAll('section'))section.hidden=section.id!=='step-'+button.dataset.step;for(const item of document.querySelectorAll('button[data-step]'))item.setAttribute('aria-pressed',String(item===button));});
</script></html>'''
    (dest / 'index.html').write_text(page, encoding='utf-8')
    # A labeled data illustration, not a screenshot or fabricated chat transcript.
    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="740" viewBox="0 0 1200 740" role="img" aria-label="Torque demo results: recognition gap, OpenStax referral, mastery unset after completion, simulated assessment demonstrated once">
<rect width="1200" height="740" rx="20" fill="#0c1421"/>
<g font-family="Arial,sans-serif"><text x="48" y="52" fill="#82d8c1" font-size="14" letter-spacing="2">EXAM RESOURCE ORCHESTRATOR / TORQUE WALKTHROUGH</text>
<text x="48" y="108" fill="#eef5ff" font-size="34" font-weight="700">From a misconception to a fresh attempt.</text>
<text x="48" y="143" fill="#aabdd3" font-size="16">Generated from real engine output. Synthetic learner evidence. No AI model invoked.</text>
<rect x="48" y="177" width="1104" height="139" rx="12" fill="#16253a"/>
<text x="72" y="208" fill="#82d8c1" font-size="13">01 / FIND THE GAP</text><text x="72" y="243" fill="#eef5ff" font-size="22">Force magnitude alone does not determine turning effect.</text>
<text x="72" y="280" fill="#c4d1e2" font-size="17">Diagnostic: {e(gap.kind)} gap / 1 of 3 supplied criteria met</text>
<rect x="48" y="334" width="1104" height="151" rx="12" fill="#16253a"/>
<text x="72" y="366" fill="#82d8c1" font-size="13">02 / REAL TYPESCRIPT CATALOG RESULT</text><text x="72" y="404" fill="#eef5ff" font-size="23">{e(source['title'])}</text>
<text x="72" y="438" fill="#9adcf6" font-size="15">{e(source['url'])}</text><text x="72" y="465" fill="#c4d1e2" font-size="15">Original link + study task + follow-up / Content downloaded: false / Mastery updated: false</text>
<rect x="48" y="503" width="1104" height="153" rx="12" fill="#16253a"/>
<text x="72" y="535" fill="#82d8c1" font-size="13">03 / SEPARATE PYTHON ASSESSMENT ENGINE</text><text x="72" y="572" fill="#eef5ff" font-size="23">After study completion: mastery = null</text>
<text x="72" y="607" fill="#c4d1e2" font-size="17">After simulated rubric assessment: demonstrated_once / 3 of 3 supplied marks</text>
<text x="72" y="636" fill="#c4d1e2" font-size="15">No causal claim. No synchronization with LearnHarness graph or sessions.</text>
<text x="48" y="700" fill="#aabdd3" font-size="14">Documentation illustration, not a product screenshot / Reproduce: python scripts/demo_torque.py</text></g></svg>'''
    (ROOT / 'docs/assets/torque-demo-results.svg').write_text(svg, encoding='utf-8')

    print('PASS: real TypeScript catalog result; completion leaves mastery null; simulated assessment records demonstrated_once; no causal attribution.')
    print('Open docs/demo/index.html or serve the repository with python -m http.server 8765 --bind 127.0.0.1')

if __name__ == '__main__':
    run()
