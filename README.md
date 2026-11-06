# Exam Resource Orchestrator — Module 16

A standalone Python module that turns a diagnosed knowledge gap into a small set of learning prescriptions, then records independent assessment results locally. Python 3.11+; no runtime dependencies, mandatory external provider, model service, or web application.

This workspace did not contain the existing Exam Reverse Engineer repository. This package implements Module 16 with integration points; it does not claim to have modified an absent core or implemented Modules 1–15.

## Run in under five minutes

Clone the private repository while signed in to GitHub, then enter its directory:

```powershell
git clone https://github.com/ahammadshibil/exam-resource-orchestrator.git
cd exam-resource-orchestrator
```

Python 3.11 or newer must be installed (`python --version`). Run these commands from the repository directory:

```powershell
python -m exam_resources --db demo.sqlite3 providers
python -m exam_resources --db demo.sqlite3 diagnostic torque
python -m exam_resources --db demo.sqlite3 recommend examples/torque.json
python -m exam_resources --db demo.sqlite3 start examples/torque.json
python -m unittest discover -s tests -v
```

`examples/torque.json` contains a **synthetic diagnostic result**, not real student evidence. For a real learner, administer the diagnostic and use `diagnose` to construct the gap. `recommend` previews without starting an intervention. `start` persists the selected prescription and reserves an unseen assessment. It prints an intervention UUID.

```powershell
python -m exam_resources --db demo.sqlite3 activity INTERVENTION_UUID completed
python -m exam_resources --db demo.sqlite3 mastery demo-learner torque
```

Mastery remains `null` until a response is assessed. After the learner has attempted the follow-up independently, an assessor can obtain its reference answer and criteria:

```powershell
python -m exam_resources --db demo.sqlite3 rubric INTERVENTION_UUID
python -m exam_resources --db demo.sqlite3 assess examples/assessment.json
python -m exam_resources --db demo.sqlite3 history demo-learner
python -m exam_resources --db demo.sqlite3 plan examples/plan.json
```

Replace the placeholder intervention and assigned assessment IDs in `examples/assessment.json`, insert the actual learner response, and mark each rubric criterion. Scores are rubric marks supplied by a learner, tutor, or teacher; there is no hidden automatic grader. The assessor label records provenance, not authenticated identity. Keep reference answers away from learners until after their response.

Optional installation: `python -m pip install .` adds the `exam-resources` command. Running `python -m exam_resources` from this directory requires no installation or network access.

## Python API

```python
from exam_resources import Orchestrator, ResourceMetadataStore, Learner

store = ResourceMetadataStore("progress.sqlite3")
engine = Orchestrator(store)
learner = Learner("student-17", "JEE", online=False)
print(engine.diagnostic("torque"))
gap = engine.diagnose("torque", "The larger radial force must turn it more", [False, False, True])
print(engine.recommend(learner, gap))
intervention = engine.start(learner, gap)
engine.tracker.record(intervention["intervention"], "completed")
# Later: collect an independent response and score it against the assigned rubric.
store.close()
```

Supply existing core diagnostics as `Gap` objects with explicit evidence. A syllabus-only gap has `confirmed=False` and `baseline=None`; it produces a diagnostic rather than an invented diagnosis. Unknown concepts request reviewed instructional content. Integrate mastery updates through the return value of `engine.evaluator.evaluate(...)`; no opening/completion event should update the host mastery engine.

## Configuration and content

- `--db PATH`: local SQLite state. No records are transmitted to providers.
- `--catalog FILE`: additional authorized resource metadata array, using fields in `exam_resources/models.py` and `data/catalog.json`. Pass the file on subsequent CLI invocations too. Resources are persisted for audit, but imported providers are not silently enabled later.
- `--topics FILE`: concept dictionary merged with starter topics. Use the shape in `data/topics.json`: diagnostic prompt, rubric and failure kinds; activity, focus, recall, misconception; and independently authored assessment IDs, prompts, answers and rubrics.
- `--weights FILE`: every factor in `DEFAULT_WEIGHTS`, with finite nonnegative values and a positive total.
- Python `ProviderRegistry.register(adapter)` / `remove(id)` adds or disables providers. A `ProviderAdapter` exposes `id`, `capabilities`, and `discover(concept)`.

The initial catalog contains original local practice plus OpenStax links and conservatively marked Khan Academy/PhET candidates. Empty registry slots cover official examinations, NCERT, DIKSHA, SWAYAM, NPTEL, MIT OCW, university materials, YouTube, and uploads. These are configurable metadata adapters, **not implemented remote search integrations**. Add verified resources or implement a documented provider API behind the same protocol. No scraping is performed.

The metadata schema records mapping evidence, prerequisites, formats, language, unknown duration, access, restrictions, license, verification, evidence, quality and learning outcomes. Unknown review quality remains `null`; ranking policy estimates are returned separately as factors. External links are HTTPS-validated syntactically; a URL's existence and current content require separate verification. Seed verification evidence is recorded per resource, and old checks receive a warning after 30 days. Khan video playback and PhET execution are unverified.

## Behavior and limits

Access filters run before ranking. Paid/unknown prices, entitlements, known regional restrictions, age eligibility, prerequisites, accessibility and available time are respected. Unknown restrictions cannot be discovered without provider metadata. Country-specific or age-limited content is excluded if eligibility is unknown. No supported language match produces an explicit warning; no translation is fabricated. Hindi torque instruction is included; the starter diagnostics, rubrics and follow-up assessment remain in English.

The ranking rubric covers relevance, authority, exam mapping evidence, prerequisites, explanatory quality, representation, language/accessibility, time, cost, verification, observed outcomes, preference and exploration. It never uses views, search position or popularity. Authority values are disclosed policy priors. Seed exam mappings are deliberately unverified; JEE/NEET examples test tutoring workflow rather than certify current syllabus coverage. Longer resources receive more time preference when `deeper=True`, but still must fit the budget.

An intervention stores the starting performance, evidence, intended outcome, exact prescription and assigned question. Engagement/completion and performance are separate events. Outcomes record the learner response, rubric marks, assessor, observed change, delayed flag and low-confidence noncausal interpretation. Sparse improvement is shrunk toward neutral in ranking. A failed intervention changes the next resource when an eligible alternative exists. An untried-resource bonus supports limited deterministic exploration.

Each starter topic has three unseen questions. A question is reserved at `start`; assessment IDs cannot be reused for that learner/concept. Exhaustion requests authored material rather than recycling a seen question as independent evidence. Delayed submissions require at least 24 hours since prescription creation; begin the reserved retention intervention ahead of the due date. These timestamps demonstrate elapsed time, not controlled retention conditions. Confounders are not measured, so the system makes no causal efficacy claims.

Study plans order diagnosed gaps by baseline, budget instruction plus assessment, schedule one teaching session a day, reserve revision minutes at approximately +1/+7 days, stop at the exam date, and provide a local fallback when available. Review days shift to fit the daily budget. Pending diagnostics, exhausted questions and sessions that cannot fit are explicit. The syllabus input is a list of concept gaps; this module does not extract a syllabus from a PDF or infer exam importance without evidence.

SQLite files contain private learning history in plain local storage. This single-user module supplies no account authentication or encryption. Keep the database under the host application's existing access controls. There is no external transfer of progress and no arbitrary binary document upload.

See [provider verification](docs/PROVIDERS.md), [architecture and data model](docs/ARCHITECTURE.md), [Codex workflow](docs/CODEX_WORKFLOW.md), [evaluation](docs/EVALUATION.md) and [roadmap](ROADMAP.md).

## Contributing

Keep providers optional and side effects explicit. Add source evidence for metadata changes. Extend tests when adding access rules, diagnostics, prescriptions or assessment behavior. New topic content needs subject review; new remote integrations need official documentation and authorized live testing. Do not commit learner databases or tokens.
