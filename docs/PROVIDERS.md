# Provider capability verification

Documentation inspected on 6 November 2026. Documentation verification is separate from authenticated integration testing. No external account was connected, no notebook created, and no source uploaded during implementation.

| Provider | Implemented behavior | Verification and limits |
|---|---|---|
| Local activities | Metadata discovery, embedded text, practice instructions | Original authored activities for three concepts; Hindi torque instruction |
| OpenStax | Local catalog search and direct section links | Official sections inspected; no chapter scraping, copying or redistribution |
| Khan Academy | Local lesson metadata and manual link | Official indexed torque lesson; playback unverified; no legacy API dependency |
| PhET | Manual Balancing Act link and targeted balance activity | Landing page resolved; simulation execution unverified; no bundled simulation |
| Gemini Notebook | Opt-in official REST create-notebook and add-source methods | Request-contract tests use injected transport; live credentials unavailable |
| Other categories | Empty configurable catalog adapters | No remote access, supported lesson or API claim |

## Link-first reference mode (v0.2, 7 November 2026)

`ReferenceService` provides a persistent reference index independent of authored diagnostics. Import original-page metadata with `add-reference` or use optional `BraveReferenceSearch`. The [official Brave documentation](https://api-dashboard.search.brave.com/app/documentation/web-search) describes the search endpoint and subscription-token authentication used by this adapter. Only titles, URLs, query provenance and explicit metadata are retained. Search result snippets, fetched page contents and credentials are not saved. A search result's actual language is unknown until separately confirmed; requesting a language is not proof that the result uses it.

Live search is opt-in and needs a separately configured `BRAVE_SEARCH_API_KEY`; no credential was present during implementation. Ordinary saved-reference search needs no provider account. A connected Codex search tool can supply a title/URL for metadata import instead. The implementation does not scrape search-result HTML or use an unofficial search endpoint.

`LinkVerifier` is an opt-in HEAD-only status checker. It blocks non-public DNS destinations and custom ports, does not follow redirects or bypass restrictions, and never reads response bodies. A HEAD failure is not automatically a broken lesson: unsupported checks, rate limits and network failures remain unknown. Original links survive restriction, unknown-cost and unknown-license conditions with clear access notes. Reference mode does not certify content coverage or feed mastery scores from link clicks or generic self-checks.

New seed references were discovered from official indexed metadata: [OpenStax photosynthesis](https://openstax.org/books/biology-2e/pages/8-1-overview-of-photosynthesis) and [MIT OCW eigenvalues](https://ocw.mit.edu/courses/18-06sc-linear-algebra-fall-2011/resources/lecture-21-eigenvalues-and-eigenvectors-1/). Content/playback and reuse licenses remain unverified; the reference workflow does not copy either source.

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
