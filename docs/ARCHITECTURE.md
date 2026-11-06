# Architecture and integration

`Orchestrator` composes the independent module. `ProviderRegistry` owns optional adapters; `ResourceDiscovery` queries only registered providers and persists their metadata. `ResourceMatcher` filters access and prerequisite incompatibilities before `RecommendationRanker` applies disclosed configurable policy factors. `LearningPrescriptionGenerator` binds a section and active task to an independent assessment. `ActivityTracker` records reported activity; `OutcomeEvaluator` records assessment evidence and updates local mastery.

The default adapters search an authorized local metadata catalog. Discovery catches ordinary provider availability/metadata failures and exposes the provider error type while continuing other providers. Programming errors are not silently swallowed. Removed providers do not reappear from cached records. The optional Gemini adapter exposes external write methods separately from discovery, with explicit authorization gates.

## Persistent data model

| Table | Identity | Stored data |
|---|---|---|
| resources | Resource ID | Full `Resource` schema, including provenance and verification |
| interventions | UUID | Learner, concept, resource, timestamp, diagnostic, exact prescription and reserved assessment |
| events | Increasing local ID | Intervention, event kind, timestamp, activity or assessment evidence |
| mastery | Learner + concept | Latest independent score, assessor, status and optional retention score |

Every recommendation includes resource evidence and a factor breakdown. Prescriptions contain objective rationale, section, activity, focus, misconception, recall task, assigned follow-up and timebox. Assessment reference answers remain in the local assessor view. The CLI's recommendation/start/history outputs omit reference answers, but its `rubric` command is intentionally assessor-facing. This is a single-user library, not a security boundary between student and assessor accounts.

## Existing-core integration contract

1. Convert the host's diagnosed concept, failure category, misconception and scored evidence into `Gap`. Supply a stable learner identifier and curriculum label in `Learner`; leave a syllabus-only gap unconfirmed.
2. Use the host's authorized metadata providers via `ProviderAdapter`. Add topic definitions through `Orchestrator(topics=...)`; unsupported content stays pending authoring.
3. Preview with `recommend`, then commit the chosen eligible activity with `start`. Save the returned intervention UUID in the host's session record.
4. Send engagement and completion to `tracker.record`. These must never count as mastery evidence.
5. Collect a fresh response, have an assessor mark the rubric, and call `evaluator.evaluate`. Forward that result, provenance and uncertainty to the host's mastery engine. Self-scored records should retain that label in the host.
6. Use the updated score to rediagnose or schedule a reserved unseen retention question. Stop on question exhaustion until reviewed questions are added.

No existing host storage or CLI entrypoint was available to patch. Use this package as a dependency or copy its independent module into the host; attach these contracts to the host API/CLI when that repository becomes available. SQLite schema initialization is idempotent for this initial version; future schema changes require explicit migrations. The implementation is single-process and does not guarantee concurrent assessment reservation across multiple processes.
