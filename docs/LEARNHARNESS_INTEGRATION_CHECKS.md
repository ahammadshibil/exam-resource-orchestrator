# LearnHarness integration checks

Integration branch: `codex/learnharness-integration`. Upstream base: `amosblomqvist/learnharness@da08cb5f7d098598ba963c6689b22054c9f2a5a3`. The full upstream application is preserved in `learnharness/`; the existing Python module remains at the repository root.

Local verification on Windows, Node 24.2.0:

- TypeScript `tsc --noEmit`: passed.
- ESLint: zero errors; one existing `source-name-ui.test.tsx` warning about `<head>`.
- Targeted integration/agent/question/practice/prompt/graph/tool regressions: 148 tests passed, zero failures.
- Production Next.js build: passed.
- Native provider-runtime smoke: all 10 native chat implementations evaluated offline; zero network attempts.
- Standalone payload check: passed, including all catalog assets and attribution.
- Packaged-server smoke: homepage and graph/model/settings endpoints returned HTTP 200.

The initial broad upstream fixture run was stopped after encountering existing Windows-specific file-permission/process-signal failures and a missing development Electron runtime (dependencies were installed with lifecycle scripts disabled). It is not reported as a passing full upstream suite. The root GitHub integration workflow runs the full suite on Ubuntu 24.04 / Node 26, matching the upstream quality job, plus the Python tests and production/standalone checks. Its result must be checked separately.

No real LLM session was executed, no API credentials were configured or bundled, and no installer was signed or released. Native resource-tool tests verify original-link discovery and phase registration, not model-driven pedagogical accuracy. Resource referrals do not mutate LearnHarness mastery or conflate its knowledge graph with the Python assessment record.
