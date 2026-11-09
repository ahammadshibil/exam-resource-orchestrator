# Exam Resource Orchestrator

Adaptive tutoring with a link-first learning resource catalog. Built on [LearnHarness](https://github.com/amosblomqvist/learnharness), this project helps learners identify a knowledge gap, find relevant external material, study actively, and attempt an independent follow-up.

[![Integration checks](https://github.com/ahammadshibil/exam-resource-orchestrator/actions/workflows/learnharness-integration.yml/badge.svg)](https://github.com/ahammadshibil/exam-resource-orchestrator/actions/workflows/learnharness-integration.yml)

## What you can do

- Use LearnHarness's probing, teaching and practice workflows, with resource discovery available to all three agents.
- Find original links across **6,454 HackerTube references** and **9,017 publisher references** from OpenStax, NPTEL and MIT OpenCourseWare.
- Reach official NCERT, DIKSHA, SWAYAM and NTA directories through clearly labeled manual discovery routes.
- Receive a study task and a fresh follow-up instruction alongside a recommended resource.
- Run an independent Python CLI/API for reference search, reviewed-topic prescriptions, rubric assessment and local SQLite history.

The resource tool stores and searches metadata; it does not download lessons, videos or transcripts. If copying permission is unknown, it can still return the original link with access and verification caveats. This behavior applies to the resource tool; other LearnHarness tools retain their own file and research capabilities.

## Quick start: tutoring app

Install Git, **Node.js 26** and npm. Then:

```sh
git clone https://github.com/ahammadshibil/exam-resource-orchestrator.git
cd exam-resource-orchestrator/learnharness
npm ci
npm run dev -- --hostname 127.0.0.1
```

Open <http://127.0.0.1:3000>. Configure a model provider in the app's settings and start a lesson. Model access may require your own account, API key and payment depending on the provider. No credentials are included. Searching the bundled catalog needs no search key; conversational tutoring needs a configured model.

Try:

> Help me understand torque. Diagnose my difficulty first, suggest one useful external resource, and test me after I study it.

Optional live discovery uses the app's configured search provider when requested by the resource tool. It sends the topic query externally; the bundled metadata search works locally. See [integration details](learnharness/UPSTREAM_INTEGRATION.md) for configuration, data boundaries and packaging.

## Quick start: Python CLI

Requires **Python 3.11+**, with no runtime dependencies. Run from the repository root:

```sh
python -m exam_resources sources
python -m exam_resources references "linear algebra" --provider nptel
python -m exam_resources references "photosynthesis" --provider openstax
python -m exam_resources --db demo.sqlite3 diagnostic torque
python -m exam_resources --db demo.sqlite3 recommend examples/torque.json
```

The example diagnostic is synthetic. Use real diagnostic responses before making learner-specific decisions. The reviewed assessment workflows cover torque, cell division and hypothesis-test selection; arbitrary-topic referrals use general study prompts and cannot update mastery. See the [Python guide](docs/PYTHON_GUIDE.md) for diagnostics, assessment, storage, live search and API examples.

## How it works

1. Diagnose a difficulty through the tutoring conversation or a reviewed Python diagnostic.
2. Search titles, topic tags and publisher locators, optionally filtering by provider.
3. Return a small number of original links, access warnings and an active-study task.
4. Ask for fresh independent work after studying. Opening a link is not evidence of learning.

LearnHarness's knowledge graph and the Python assessment history are separate stores. A graph entry does not establish mastery, and this integration does not synchronize the two stores.

## Coverage and limitations

This is an experimental integration, not a complete exam platform or a validated measure of educational effectiveness. It does not implement an absent Exam Reverse Engineer Modules 1–15 codebase.

Catalog search is lexical. References are discovery candidates, not guaranteed curriculum matches. OpenStax and MIT sitemap labels are derived from URLs and have not been verified against page headings. Availability, language, price, regional access and instructional accuracy can be unknown. Manual discovery routes are catalog starting points, not specific lesson matches.

Catalog counts describe the bundled snapshots, not continuously updated coverage. See [index sources](docs/INDEX_SOURCES.md) and [third-party notices](THIRD_PARTY_NOTICES.md). Desktop sources are included, but this integration does not publish a signed installer or claim validation of a real model-driven teaching session.

## Development

```sh
# Repository root
python -m unittest discover -s tests -v

# App (Linux / Node 26 is the CI environment)
cd learnharness
npm ci
npm run typecheck
npm test
npm run lint
npm run build
node scripts/smoke-provider-runtime.mjs
node scripts/build-server.mjs
node scripts/smoke-server.mjs
```

Some upstream tests rely on Unix permissions and process signals. Use the Linux CI environment for the complete app suite. After changing the Python catalog snapshots, run `node scripts/sync-learning-catalog.mjs` from `learnharness/`; tests verify that the app copies match.

## Repository map

| Path | Purpose |
| --- | --- |
| `learnharness/` | Full upstream tutoring app plus the resource-tool integration |
| `exam_resources/` | Standalone Python engine, CLI and metadata |
| `examples/` | Synthetic inputs and integration examples |
| `tests/` | Python tests; app tests live in `learnharness/tests/` |
| `docs/` | Source provenance, Python guide and integration verification |

## Contributing

Read [CONTRIBUTING.md](CONTRIBUTING.md) before opening a pull request. Report reproducible bugs through [GitHub Issues](https://github.com/ahammadshibil/exam-resource-orchestrator/issues). Never include API keys, learner files or private progress databases in an issue or commit.

## License and attribution

Project code is licensed under **GNU AGPL v3.0 only**; see [LICENSE](LICENSE). LearnHarness is by its upstream contributors, imported from v0.5.0 at commit `da08cb5f7d098598ba963c6689b22054c9f2a5a3`. Its original license and notices remain in `learnharness/`. This project is an independent derivative and implies no upstream endorsement.

Catalog metadata and external teaching material have separate rights. HackerTube's included reduced database carries ODC-By attribution requirements. The project license does not license linked videos, books or courses. Preserve [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md) when redistributing the catalogs.
