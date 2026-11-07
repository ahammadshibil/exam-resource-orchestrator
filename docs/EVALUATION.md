# Evaluation framework

Run `python -m unittest discover -s tests -v`. The suite is offline and uses temporary SQLite files. On hosts with a restricted system temp directory, set `EXAM_TEST_TMP` to a writable scratch directory first. Tests currently comprise 38 cases.

| Acceptance scenario | Verified behavior |
|---|---|
| A: JEE torque recognition | Rubric diagnoses recognition; torque activity, fresh question and persisted outcome |
| B: NEET mitosis/meiosis | Homologue/sister confusion, chromosome tracking and independent follow-up |
| C: University test selection | Sampling-unit activity, paired-test diagnosis and unfamiliar design question |
| D: Syllabus only | No assumed deficit; diagnostic required before prescription |
| E: No internet | Embedded local content; no URL or provider required |
| F: Paid/blocked preferred provider | Explicit exclusion before ranking; eligible alternative |
| G: Regional language | Hindi torque activity selected; local progress and follow-up retained |

All seven scenarios check actionable sections/tasks, relevant concept coverage, follow-up without exposed answers, completion/mastery separation, outcome persistence, and reopening the database. These are synthetic scenarios and deterministic workflow checks, not evidence that the activities improve actual exam results. Regional-language assessment is still English. Exam labels do not imply verified syllabus mapping.

Additional tests cover access/prerequisite/time/age/region constraints, provider failure and removal, explicit empty registries, unknown languages/concepts, malformed metadata and numeric scores, ranking configuration, failure-triggered resource changes, unseen-question exhaustion, incorrect assessment IDs, duplicate/early/non-independent assessment rejection, delayed retention persistence, daily plan capacity, notebook authorization and documented REST payloads, and CLI start/completion.

The v0.2 reference suite adds arbitrary topics without an authored diagnostic, permission-unknown and cost-unknown link retention, restricted/dead/redirected link labels, HEAD-only transport with no body reads, rejection of private network destinations by the checker, content/metadata verification separation, reference-only content rejection, persistent deduplication, search contract and metadata-only retention, credential-free imports, no implicit network calls, offline behavior, safe provider-error fallback, access-aware ordering, reviewed-tutoring candidate integration, preservation of reviewed metadata during re-discovery, exact query/fragment preservation and CLI import/search. Seeded photosynthesis and eigenvalue reference commands were smoke-tested. Brave API behavior is transport-contract tested; no live Brave credential was available.

A live HEAD-only check of the seeded OpenStax photosynthesis URL returned a reachable status on 7 November 2026. No response body was read, and the content-verification and licensing fields remained unverified. This check is not a guarantee of access from another learner's account or region.

Official external source URLs were checked using browsing during development; runtime tests make no network requests and cannot certify continuing availability. Khan playback and PhET execution remain unverified in seed metadata. Google API requests are contract-tested with an injected transport, not authenticated live. No simulation/license redistribution was tested or attempted.

Source CLI recommendation and plan commands were smoke-tested successfully. The source ZIP passed archive integrity verification. An optional wheel build stalled in the local build environment and was interrupted; installed-wheel execution is not verified. Run directly from the supplied source directory as described in the README.

Before production integration, review topic pedagogy and translations with subject experts, verify each current exam mapping against an official syllabus, test the optional notebook adapter using an authorized eligible account, and add assessments representative of the host curriculum. Monitor recommendation coverage, access exclusions, diagnostic completion, immediate independent scores, delayed retention, and within-learner resource diversity. Report missing baselines and self-reported scores separately. Observed gains remain confounded; causal claims require a suitable study design.
