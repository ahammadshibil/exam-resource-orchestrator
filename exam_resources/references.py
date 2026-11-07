"""Persistent link discovery. Teaching pages are neither downloaded nor copied."""
from dataclasses import asdict, replace
import hashlib
import ipaddress
import json
import re
import socket
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urlsplit, urlunsplit
from urllib.request import Request, HTTPRedirectHandler, build_opener, urlopen
from .models import Resource, now
from .engine import ResourceMatcher, RecommendationRanker


def canonical_link(url):
    parts = urlsplit(url)
    if parts.scheme != "https" or not parts.hostname or parts.username or parts.password:
        raise ValueError("References require an HTTPS URL without credentials")
    if parts.port not in {None, 443}:
        raise ValueError("References must use the standard HTTPS port")
    # Preserve query strings and fragments: they can identify lessons and sections.
    return urlunsplit(("https", parts.netloc.lower(), parts.path or "/", parts.query, parts.fragment))


def reference_id(url):
    return "ref-" + hashlib.sha256(canonical_link(url).encode()).hexdigest()[:24]


def tokens(text):
    return set(re.findall(r"[^\W_]+", text.casefold(), re.UNICODE))


def query_terms(text):
    text = re.sub(r"^\s*what\s+(?:is|are)\s+", "", text, flags=re.IGNORECASE)
    return tokens(text) - {"a", "an", "and", "the", "of"}


def metadata_confidence(resource):
    return (resource.availability == "verified", resource.title_basis == "source_metadata", resource.verified_at or "")


def access_note(resource, learner):
    reason = ResourceMatcher.exclusion(resource, learner)
    if resource.link_status in {"restricted", "unavailable"}:
        reason = f"Link check: {resource.link_status}; manual access may differ"
    notes = [f"Content {resource.availability}; link {resource.link_status}."]
    if reason:
        notes.append(reason)
    if resource.language != learner.language:
        notes.append(f"Requested language {learner.language}; source language {resource.language}. Translation not assumed.")
    if resource.reference_only:
        notes.append("Original page only; no content retrieval or reuse permission required by this workflow.")
    if resource.title_basis == "publisher_url_label":
        notes.append("Locator label derived from a publisher URL; the source title and content have not been inspected.")
    return " ".join(notes), reason is not None


class BraveReferenceSearch:
    """Optional documented search API. Only titles and URLs are retained."""
    def __init__(self, key, transport=None):
        if not key:
            raise ValueError("Set BRAVE_SEARCH_API_KEY for live search, or import references without a search key")
        self.key = key
        self.transport = transport or self._http

    @staticmethod
    def _http(url, headers):
        request = Request(url, headers=headers)
        with urlopen(request, timeout=15) as response:
            return json.load(response)

    def search(self, query, language="en"):
        if not query.strip() or len(query) > 600 or len(query.split()) > 75:
            raise ValueError("Search query must be nonempty and within the provider's query limits")
        params = urlencode({"q": query, "search_lang": language, "count": 10, "safesearch": "strict"})
        response = self.transport("https://api.search.brave.com/res/v1/web/search?" + params,
                                  {"X-Subscription-Token": self.key, "Accept": "application/json"})
        result = []
        for item in response.get("web", {}).get("results", []):
            try:
                url = canonical_link(item["url"])
                title = item["title"].strip()
                if not title:
                    continue
                result.append(Resource(id=reference_id(url), provider="web-references", title=title,
                                       url=url, concepts=[query], section="Exact section not verified; locate this topic on the original page",
                                       language="und", format="unknown", reference_only=True,
                                       mapping_evidence="Search-query candidate; concept coverage and curriculum mapping unverified",
                                       evidence=[f"Discovered using official Brave Search API at {now()}; query: {query}"],
                                       permitted_usage="Link only; permission to copy content is not assumed"))
            except (KeyError, ValueError, TypeError, AttributeError):
                continue
        return result


class NoRedirects(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


class LinkVerifier:
    """HEAD-only check. A reachable URL does not verify its lesson content."""
    def __init__(self, transport=None):
        self.transport = transport or self._head

    @staticmethod
    def _head(url):
        parts = urlsplit(canonical_link(url))
        addresses = socket.getaddrinfo(parts.hostname, 443, type=socket.SOCK_STREAM)
        if not addresses or any(not ipaddress.ip_address(item[4][0]).is_global for item in addresses):
            raise ValueError("Only public internet addresses may be checked")
        # No redirects, cookies, login attempts, GET fallback or response-body reads.
        request = Request(url, method="HEAD", headers={"User-Agent": "ExamResourceLinkCheck/0.2"})
        with build_opener(NoRedirects()).open(request, timeout=10) as response:
            return response.status

    def check(self, resource):
        if not resource.url:
            raise ValueError("Resource has no external link")
        try:
            status = self.transport(canonical_link(resource.url))
        except HTTPError as error:
            status = error.code
            error.close()
        except (URLError, OSError, ValueError):
            status = None
        if status is not None and 200 <= status < 300:
            state = "reachable"
        elif status in {401, 402, 403, 451}:
            state = "restricted"
        elif status in {404, 410}:
            state = "unavailable"
        elif status is not None and 300 <= status < 400:
            state = "redirect"
        else:
            state = "unknown"
        resource.link_status = state
        resource.link_checked_at = now()
        # Keep content availability, evidence and permission unchanged.
        return resource


class ReferenceService:
    def __init__(self, store, catalog=(), search_provider=None, verifier=None, excluded_providers=(), included_providers=()):
        self.store, self.catalog = store, list(catalog)
        self.search_provider = search_provider
        self.verifier = verifier or LinkVerifier()
        self.excluded_providers = set(excluded_providers)
        self.included_providers = set(included_providers)

    def add(self, metadata):
        metadata = dict(metadata)
        forbidden = {"content", "offline", "id", "reference_only"} & metadata.keys()
        if forbidden:
            raise ValueError("Reference import accepts metadata only; omit content, offline, id and reference_only")
        url = canonical_link(metadata["url"])
        resource = Resource(**{**metadata, "url": url, "id": reference_id(url), "reference_only": True})
        self.store.put(resource)
        return resource

    def search(self, query, learner, *, limit=2, live=False, check_links=False):
        if not query.strip() or not 1 <= limit <= 10:
            raise ValueError("Supply a topic and a limit between one and ten")
        errors = []
        live_urls = set()
        if live:
            if not learner.online:
                raise ValueError("Live discovery requires internet; use saved references offline")
            if self.search_provider is None:
                errors.append("Live search is not configured; use BRAVE_SEARCH_API_KEY or import metadata from a connected search tool")
            else:
                try:
                    from .sources import sources, source_for_url
                    domains = [domain for source in sources() if source["id"] in self.included_providers for domain in source["domains"]]
                    search_query = query + (" (" + " OR ".join("site:" + domain for domain in domains) + ")" if domains else "")
                    for resource in self.search_provider.search(search_query, learner.language):
                        resource.provider = source_for_url(resource.url) or resource.provider
                        if self.included_providers and resource.provider not in self.included_providers:
                            continue
                        if query not in resource.concepts:
                            resource.concepts.append(query)
                        live_urls.add(canonical_link(resource.url))
                        previous = next((r for r in self.store.resources() if r.id == resource.id), None)
                        # Re-discovery must not overwrite reviewed metadata or link checks.
                        if previous is None:
                            self.store.put(resource)
                except (OSError, ValueError, TimeoutError):
                    errors.append("Live search failed; retained saved references. No provider response or credential was logged.")
        found = {}
        for resource in [*self.catalog, *self.store.resources()]:
            if not resource.url or resource.provider in self.excluded_providers:
                continue
            if self.included_providers and resource.provider not in self.included_providers:
                continue
            coverage = tokens(" ".join([resource.title, *resource.concepts, resource.section]))
            wanted = query_terms(query)
            if not wanted or (not wanted.issubset(coverage) and canonical_link(resource.url) not in live_urls):
                continue
            url = canonical_link(resource.url)
            existing = found.get(url)
            if existing and metadata_confidence(existing) > metadata_confidence(resource):
                if resource.link_checked_at and resource.link_checked_at > (existing.link_checked_at or ""):
                    existing = replace(existing, link_status=resource.link_status, link_checked_at=resource.link_checked_at)
                found[url] = existing
            else:
                found[url] = resource
        ranker = RecommendationRanker(self.store)
        # Referral scores express metadata relevance and authority, never learning efficacy.
        from .models import Gap
        gap = Gap(query, "unknown", "Learner has requested this topic; no deficit inferred", None, "Topic request")
        ranked = []
        for resource in found.values():
            score, factors = ranker.score(resource, learner, gap)
            exact_tag = query.casefold() in {c.casefold() for c in resource.concepts}
            if exact_tag and resource.availability == "verified":
                relevance = 1.
            elif query.casefold() in resource.title.casefold():
                relevance = .8
            elif query_terms(query).issubset(tokens(resource.title)):
                relevance = .7
            else:
                relevance = .6 if exact_tag else .4
            factors["concept"] = relevance
            score = round(sum(factors[k] * w for k, w in ranker.weights.items()) / sum(ranker.weights.values()), 4)
            note, blocked_or_unknown = access_note(resource, learner)
            metadata = asdict(resource)
            metadata["content"] = None
            item = {"resource": metadata, "score": score, "factors": factors,
                    "access_note": note, "access_blocked_or_unknown": blocked_or_unknown,
                    "why": f"Metadata matches your request for {query}; inspect the original page to confirm the exact coverage.",
                    "section": resource.section,
                    "activity": (f"Open this {resource.reference_kind} and choose the relevant chapter or lecture for {query} before studying. " if resource.reference_kind in {"course", "book", "catalog"} else "Open the original link. ") + f"Locate {query}. State your question first; then write a short explanation and work one example from the relevant section. If access is blocked, use another listed source.",
                    "follow_up": f"Close the page. Explain {query} in your own words and apply it to a different example; identify any uncertainty for a tutor to check.",
                    "assessment_status": "Self-check only; use a reviewed independent assessment before updating mastery"}
            ranked.append(item)
        # Usable resources first, but permission/access restrictions never discard links.
        ranked.sort(key=lambda r: (r["access_blocked_or_unknown"], -r["score"], r["resource"]["url"]))
        if check_links and learner.online:
            for item in ranked[:limit]:
                resource = self.verifier.check(Resource(**item["resource"]))
                self.store.put(resource)
                item["resource"] = asdict(resource)
                item["access_note"], item["access_blocked_or_unknown"] = access_note(resource, learner)
        return {"status": "references_found" if ranked else "no_references", "query": query,
                "references": ranked[:limit], "total_matches": len(ranked), "errors": errors,
                "content_downloaded": False, "mastery_updated": False,
                "instruction": "Follow links to original providers. Reference discovery works for any topic; scored tutoring still requires authored diagnostics and assessments."}
