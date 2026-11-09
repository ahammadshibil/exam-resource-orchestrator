# LearnHarness + Exam Resource Orchestrator

This directory contains the complete LearnHarness application imported as a Git subtree from https://github.com/amosblomqvist/learnharness at commit `da08cb5f7d098598ba963c6689b22054c9f2a5a3` (v0.5.0). The original application, license, history reference, prompts, tests and notices are preserved. Integration modifications are maintained on `codex/learnharness-integration` in the parent repository.

## Run the combined application

Use Node 26 (the upstream CI version) and npm. From the parent repository:

```powershell
cd learnharness
npm ci
npm run dev -- --hostname 127.0.0.1
```

Open `http://127.0.0.1:3000`. Configure a model in LearnHarness's provider/model settings, then begin a teaching or practice session. The catalog itself needs no model API key; conversational tutoring uses your configured model/provider. No key or external account is supplied by this repository.

Example request in a teaching session: “Help me understand torque. Diagnose my difficulty first, then suggest an external resource and test me after I use it.” The prober, teacher and practitioner can call `learning_resources`, which returns original links, a specific active-study task, access/verification caveats and a follow-up instruction. The native question/problem tools still collect and assess the learner's actual work.

The original Python module remains available at the parent repository root, with its CLI, independent rubric scoring, SQLite intervention history, study planning, metadata import and optional Notebook adapter. No existing Python progress database is migrated or overwritten. LearnHarness sessions and knowledge graphs remain governed by its original storage model; graph inclusion is not treated as mastery.

## What was connected

- Native `learning_resources` tool injected through a typed core port into all three agent phases.
- A read-only TypeScript catalog adapter, so the app does not need Python or a Python subprocess.
- The same publisher/HackerTube snapshots as the Python module, copied under `resources/learning-catalog` and checked for byte identity by tests.
- Optional live search through LearnHarness's existing configured search-provider port. Search is opt-in per tool call; snippets are not copied into catalog responses and credentials are not returned.
- Official provider filters and manual catalog routes. Unknown copying permission retains the original link, with warnings; teaching content is not downloaded by this tool.
- Concise phase-specific guidance to diagnose first, prescribe an activity, and assess a fresh unaided response afterward. Opening a resource never writes a mastery record.
- Explicit standalone tracing and payload checks for the catalog assets and their third-party notices.

After changing the Python snapshots, run `node scripts/sync-learning-catalog.mjs` from this directory before building. The sync script has a fixed allowlist of metadata files and the attribution notice; it does not copy progress databases, keys or session state.

The original research, PDF, visual and demo capabilities remain available. The metadata-only guarantee describes `learning_resources`; the upstream app's other tools retain their own behavior and permissions. Ordinary provider search can send a topic query externally when live search is requested. No learner files, credentials or progress records are uploaded by the resource tool.

## Checks and limits

Run `npm run typecheck`, `npm run lint`, and `npm test` on the upstream-supported Linux/Node 26 environment. The root integration workflow runs those checks, a production build, standalone smoke checks and the Python suite. On Windows PowerShell, `npm test`'s upstream POSIX environment assignment can be replaced by `$env:NODE_ENV='test'; node node_modules/tsx/dist/cli.mjs --test tests/*.test.ts tests/*.test.tsx`. Some existing Unix file-permission/process-signal tests are platform-sensitive.

An unsigned installer is not produced or published by this integration. Existing desktop sources are retained; native desktop packaging and real model-driven pedagogy require separate validation. The included reference snapshots are discovery candidates, not verified curriculum mappings or evidence of teaching effectiveness. The independent Python progress model and LearnHarness graph/session model are intentionally not silently conflated.

## Source and license

LearnHarness is AGPL-3.0-only; its original `LICENSE` remains in this directory. Catalog origins and metadata notices are retained at `resources/learning-catalog/THIRD_PARTY_NOTICES.md` and the parent `THIRD_PARTY_NOTICES.md`. No upstream author endorsement is implied. The subtree squash commit records the upstream source revision for future updates.
