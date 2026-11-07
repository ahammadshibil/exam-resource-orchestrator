# Provider capability verification

Documentation inspected on 6 November 2026. Documentation verification is separate from authenticated integration testing. No external account was connected, no notebook created, and no source uploaded during implementation.

| Provider | Implemented behavior | Verification and limits |
|---|---|---|
| Local activities | Metadata discovery, embedded text, practice instructions | Original authored activities for three concepts; Hindi torque instruction |
| OpenStax | Local catalog search and direct section links | Official sections inspected; no chapter scraping, copying or redistribution |
| Khan Academy | Local lesson metadata and manual link | Official indexed torque lesson; playback unverified; no legacy API dependency |
| PhET | Manual Balancing Act link and targeted balance activity | Landing page resolved; simulation execution unverified; no bundled simulation |
| Gemini Notebook | Opt-in official REST create-notebook and add-source methods | Request-contract tests use injected transport; live credentials unavailable |
| HackerTube | Bundled, attributed metadata adapter for 6,454 video references | Official export retrieved; no video playback, transcript or content verification |
| OpenStax/NPTEL/MIT expanded catalogs | 9,017 additional publisher locators and course records | Metadata snapshot only; source-title and URL-label provenance distinguished |
| NCERT/DIKSHA/SWAYAM/NTA | Explicit manual catalog discovery routes | Not indexed individual lessons or assumed examination mappings |
| Other categories | Configurable catalog adapters | No remote access, supported lesson or API claim |

## Expanded publisher indexes (v0.3)

The additional catalog contains 4,790 OpenStax section locators, 3,483 NPTEL courses and 744 MIT OCW course/section locators. Source provenance, collection boundaries and portal-check observations are recorded in [INDEX_SOURCES.md](INDEX_SOURCES.md). Publisher robots rules and public advertised sitemaps/listings were checked before collecting metadata. No teaching-page bodies or media were retrieved for these catalogs.

`sources` exposes the official directory URLs and their actual coverage. `references --provider ID` filters indexed results and returns manual catalog routes separately. Source selection also scopes optional live search to official domains; unrelated results are discarded. Unknown license/access still retains the original link. Portal access problems are disclosed: NCERT was unreachable in this environment, DIKSHA responded to HEAD, and SWAYAM's catalog resolved during browsing but rejected HEAD with 405. None of those observations certifies a particular lesson or requested language.

## Link-first reference mode (v0.2, 7 November 2026)

`ReferenceService` provides a persistent reference index independent of authored diagnostics. Import original-page metadata with `add-reference` or use optional `BraveReferenceSearch`. The [official Brave documentation](https://api-dashboard.search.brave.com/app/documentation/web-search) describes the search endpoint and subscription-token authentication used by this adapter. Only titles, URLs, query provenance and explicit metadata are retained. Search result snippets, fetched page contents and credentials are not saved. A search result's actual language is unknown until separately confirmed; requesting a language is not proof that the result uses it.

Live search is opt-in and needs a separately configured `BRAVE_SEARCH_API_KEY`; no credential was present during implementation. Ordinary saved-reference search needs no provider account. A connected Codex search tool can supply a title/URL for metadata import instead. The implementation does not scrape search-result HTML or use an unofficial search endpoint.

`LinkVerifier` is an opt-in HEAD-only status checker. It blocks non-public DNS destinations and custom ports, does not follow redirects or bypass restrictions, and never reads response bodies. A HEAD failure is not automatically a broken lesson: unsupported checks, rate limits and network failures remain unknown. Original links survive restriction, unknown-cost and unknown-license conditions with clear access notes. Reference mode does not certify content coverage or feed mastery scores from link clicks or generic self-checks.

New seed references were discovered from official indexed metadata: [OpenStax photosynthesis](https://openstax.org/books/biology-2e/pages/8-1-overview-of-photosynthesis) and [MIT OCW eigenvalues](https://ocw.mit.edu/courses/18-06sc-linear-algebra-fall-2011/resources/lecture-21-eigenvalues-and-eigenvectors-1/). Content/playback and reuse licenses remain unverified; the reference workflow does not copy either source.

## HackerTube metadata adapter (v0.2.1)

Karpathy's [project announcement](https://karpathy.bearblog.dev/hacker-tube/) points to HackerTube's data export. The official [data page](https://hackertube.org/data) and [export schema](https://hackertube.org/download/DATA.md) provide the metadata and attribution terms. On 7 November 2026, the public manifest at `https://hackertube.org/api/export` identified 6,454 video records in the 31 October snapshot; the published `https://hackertube.org/download/videos.jsonl` export was used to build this reduced index. These are the site's published export paths, not a claimed general-purpose API integration.

The included `data/hackertube.jsonl` retains only six source fields: video ID, original URL, title, channel, primary topic and tags. `HackerTubeAdapter` validates each URL against its exported YouTube ID, adds attribution and marks the result unverified. No video, transcript, summary, quote, comment, thumbnail, embedding or popularity score is imported. Source labels are discovery evidence, not demonstrated learning effectiveness or official exam alignment. Language, cost, prerequisites, duration and video licensing are not inferred. The catalog metadata license is ODC-By 1.0; original-video rights remain separate. See [THIRD_PARTY_NOTICES.md](../THIRD_PARTY_NOTICES.md).

The adapter is registered by default and can be removed through `ProviderRegistry`. It needs no key or network to search the bundled snapshot. Refreshing requires retrieving a newly published export, validating the reduced fields and updating attribution dates; no background scraper or undocumented refresh endpoint is installed.

## Gemini Notebook

The [official API overview](https://developers.google.com/notebook/docs) documents notebook/source management in public preview. This package uses the personal-account API at `https://notebook.googleapis.com/v1`, distinct from the [Enterprise API](https://docs.cloud.google.com/gemini/enterprise/notebooklm-enterprise/docs/api-notebooks-sources). The [authentication guide](https://developers.google.com/notebook/docs/authentication) specifies OAuth with notebook scope, account eligibility, initial product sign-in and quota-project configuration. Obtain credentials separately; never save tokens in learner records.

`GeminiNotebookAdapter(token, project)` uses a 20-second timeout and propagates provider errors. The caller owns credential refresh, quota handling and recovery. No retry automatically duplicates an external write. Call `create_notebook(title, authorized=True)` only after authorization to create the remote notebook. Call `add_source(name, title, url=... or text=..., authorized=True, rights_confirmed=True)` only for material explicitly authorized for transfer and licensed for that use. These are Python API operations; the ordinary study CLI never invokes them.

The [source guide](https://developers.google.com/notebook/docs/sources) documents public HTTPS and inline text sources. Source processing is asynchronous: an accepted create response does **not** establish that the source is ready. This minimal adapter returns the provider response without claiming ingestion success. Inspect readiness in the product before study; automated readiness polling is not implemented. Do not supply private URLs or login-only sources.

Google also documents an [official remote MCP server](https://developers.google.com/notebook/docs/mcp). This deliverable uses REST and does not install or configure an MCP connection. Its [roadmap](https://developers.google.com/notebook/docs/roadmap) lists further capabilities under development. Audio, video, mind maps, flashcards, quizzes, notebook querying and source-grounded interaction are learner-guided UI workflows here; no automated generation or progress exchange is claimed. Source titles can carry syllabus-unit labels; no undocumented folders endpoint is used. Copy the actual notebook link from the UI; this adapter does not fabricate a notebook deep link from its identifier.

## Links, licensing and verification

The [Khan API repository](https://github.com/Khan/khan-api) is historical documentation; it does not establish a usable supported integration today. The adapter uses no private GraphQL or session cookies. The seeded [Introduction to torque](https://www.khanacademy.org/science/in-in-class11th-physics/in-in-system-of-particles-and-rotational-motion/in-in-torque-and-equilibrium-ap/v/introduction-to-torque) is a discovery candidate with no invented duration or timestamp range.

[PhET licensing](https://phet.colorado.edu/en/licensing) currently distinguishes noncommercial simulation use and commercial permission requirements. This package only links to [Balancing Act](https://phet.colorado.edu/en/simulations/balancing-act), and does not embed or distribute simulation files. Consult current terms before adding retrieval or commercial embedding.

Seeded OpenStax sections: [torque](https://openstax.org/books/university-physics-volume-1/pages/10-6-torque), [meiosis](https://openstax.org/books/biology-2e/pages/11-1-the-process-of-meiosis), [paired samples](https://openstax.org/books/introductory-statistics-2e/pages/10-4-matched-or-paired-samples), [independent means](https://openstax.org/books/introductory-statistics-2e/pages/10-1-two-population-means-with-unknown-standard-deviations). Per-resource licenses remain conservative link-only metadata rather than assuming every asset shares one license.

Reverification procedure: open the exact official URL; verify title, concept coverage and assigned section; inspect regional, age, cost and licensing restrictions; update availability, `verified_at` and the actual evidence. A successful HTTP response alone must not promote an inaccessible lesson to content-verified status. Keep inaccessible material unverified and retain a local fallback.
