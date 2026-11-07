# Publisher reference snapshot — 7 November 2026

Version 0.3.0 adds 9,017 distinct publisher URLs, alongside the existing HackerTube and starter references. These are bibliographic/locator records, not copied lessons or a verified mapping to any examination.

| Publisher | New records | Source metadata | What was checked |
|---|---:|---|---|
| OpenStax | 4,790 | Section URLs from 20 book sitemaps | URLs occur in publisher-advertised XML; URL-derived labels explicitly distinguished from page titles |
| NPTEL | 3,483 | Course title, discipline and URL from the public course catalog | Course metadata appears in the official listing; lecture content and availability not inspected |
| MIT OCW | 744 | Course/section URLs from 10 course sitemaps | Exact locators occur in publisher XML; sitemap resource assets excluded |

The OpenStax sitemap index was discovered through [robots.txt](https://openstax.org/robots.txt): [book sitemap index](https://openstax.org/rex/sitemaps/index.xml). The selected books cover biology, chemistry, organic chemistry, college physics, university physics volumes 1–3, calculus volumes 1–3, statistics, algebra/trigonometry, anatomy/physiology, microbiology, astronomy, economics, psychology, Python, computer science and data science. Only numbered `/books/.../pages/...` locator URLs were retained. No book pages, chapter text or figures were retrieved. Labels such as `Publisher URL label: ...` are derived from locator paths and do not assert the actual section heading.

NPTEL's [official public course listing](https://nptel.ac.in/courses) exposed 3,484 titled catalog entries; deduplicating identical course URLs left 3,483 references. Only course title, discipline and original link were extracted. Author biographies, descriptions, transcripts and lectures were not copied. The site's [robots rules](https://nptel.ac.in/robots.txt) allowed catalog crawling at collection time. This is a course directory snapshot, not a supported private API or a claim of current enrollment.

MIT's [official sitemap index](https://ocw.mit.edu/sitemap.xml), advertised by [robots.txt](https://ocw.mit.edu/robots.txt), supplied the selected course sitemap URLs. The 10 courses cover single-variable calculus, multivariable calculus, linear algebra, probability/statistics, classical mechanics, electricity/magnetism, biology, chemistry, Python programming and microeconomics. Retained locators are exact course roots and `/pages/` URLs. Resource files, media, thumbnails and video bodies were not requested. Generic syllabus/calendar/staff pages were excluded. Remaining section coverage and headings are unverified.

Every record includes its publisher, original URL, exact source catalog/sitemap URL, collection date, reference kind and title basis. License, current access, instructional language and content correctness remain unknown unless independently supplied. Robots permission to retrieve metadata is not represented as permission to copy teaching material.

## Manual official discovery routes

`sources` lists 10 configured provider directories. NCERT, DIKSHA and SWAYAM are explicit manual catalog routes rather than fabricated topic-specific lessons. NTA provides an official examination starting point, not an assumed current syllabus mapping. These routes do not forward a query or guarantee that a matching resource/language exists.

On 7 November 2026, a HEAD check reached the DIKSHA explore route and an NPTEL sample course. NCERT textbook-portal access failed in this environment and remains an unverified manual link. SWAYAM's catalog resolved during browsing but returned HTTP 405 to HEAD; this is recorded as an unsupported check rather than a broken site. Access can differ by network, account and region.

## Refresh and verification

This is a fixed snapshot; no background crawler is installed. To refresh, inspect current publisher robots rules and advertised catalogs/sitemaps, extract only metadata/locators, validate provider-domain ownership, deduplicate URLs and rerun snapshot tests. Preserve known, reviewed metadata when a weaker URL-label record duplicates it. Recheck individual links only on explicit request. A HEAD result never establishes section content, reuse rights, cost, prerequisites or exam alignment.
