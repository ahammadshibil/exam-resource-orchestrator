"""Persistent link discovery. Teaching pages are neither downloaded nor copied."""
from dataclasses import asdict
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
    def __init__(self, store, catalog=(), search_provider=None, verifier=None):
        self.store, self.catalog = store, list(catalog)
        self.search_provider = search_provider
        self.verifier = verifier or LinkVerifier()

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
                    for resource in self.search_provider.search(query, learner.language):
                        live_urls.add(canonical_link(resource.url))
                        previous = next((r for r in self.store.resources() if r.id == resource.id), None)
                        # Re-discovery must not overwrite reviewed metadata or link checks.
                        if previous is None:
                            self.store.put(resource)
                except (OSError, ValueError, TimeoutError):
                    errors.append("Live search failed; retained saved references. No provider response or credential was logged.")
        found = {}
        for resource in [*self.catalog, *self.store.resources()]:
            if not resource.url:
                continue
            coverage = tokens(" ".join([resource.title, *resource.concepts]))
            wanted = tokens(query)
            if not wanted or (not wanted.issubset(coverage) and canonical_link(resource.url) not in live_urls):
                continue
            url = canonical_link(resource.url)
            found[url] = resource
        ranker = RecommendationRanker(self.store)
        # Referral scores express metadata relevance and authority, never learning efficacy.
        from .models import Gap
        gap = Gap(query, "unknown", "Learner has requested this topic; no deficit inferred", None, "Topic request")
        ranked = []
        for resource in found.values():
            if check_links and learner.online:
                resource = self.verifier.check(resource)
                self.store.put(resource)
            score, factors = ranker.score(resource, learner, gap)
            factors["concept"] = 1. if query.casefold() in {c.casefold() for c in resource.concepts} and resource.availability == "verified" else .5
            score = round(sum(factors[k] * w for k, w in ranker.weights.items()) / sum(ranker.weights.values()), 4)
            reason = ResourceMatcher.exclusion(resource, learner)
            if resource.link_status in {"restricted", "unavailable"}:
                reason = f"Link check: {resource.link_status}; manual access may differ"
            if reason is None and resource.cost == "unknown":
                reason = "Cost and access unverified"
            notes = [f"Content {resource.availability}; link {resource.link_status}."]
            if reason:
                notes.append(reason)
            if resource.language != learner.language:
                notes.append(f"Requested language {learner.language}; source language {resource.language}. Translation not assumed.")
            if resource.reference_only:
                notes.append("Original page only; no content retrieval or reuse permission required by this workflow.")
            metadata = asdict(resource)
            metadata["content"] = None
            item = {"resource": metadata, "score": score, "factors": factors,
                    "access_note": " ".join(notes), "access_blocked_or_unknown": reason is not None,
                    "why": f"Metadata matches your request for {query}; inspect the original page to confirm the exact coverage.",
                    "section": resource.section,
                    "activity": f"Open the original link. Locate {query}. State your question first; then write a short explanation and work one example from the relevant section. If access is blocked, use another listed source.",
                    "follow_up": f"Close the page. Explain {query} in your own words and apply it to a different example; identify any uncertainty for a tutor to check.",
                    "assessment_status": "Self-check only; use a reviewed independent assessment before updating mastery"}
            ranked.append(item)
        # Usable resources first, but permission/access restrictions never discard links.
        ranked.sort(key=lambda r: (r["access_blocked_or_unknown"], -r["score"], r["resource"]["url"]))
        return {"status": "references_found" if ranked else "no_references", "query": query,
                "references": ranked[:limit], "total_matches": len(ranked), "errors": errors,
                "content_downloaded": False, "mastery_updated": False,
                "instruction": "Follow links to original providers. Reference discovery works for any topic; scored tutoring still requires authored diagnostics and assessments."}
