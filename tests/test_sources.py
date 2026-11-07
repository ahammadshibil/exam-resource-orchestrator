import io
import json
import unittest
from contextlib import redirect_stdout
from dataclasses import asdict, replace
from unittest.mock import MagicMock
from exam_resources import Learner, Orchestrator, ResourceMetadataStore
from exam_resources.cli import main
from exam_resources.models import now
from exam_resources.references import ReferenceService, LinkVerifier
from exam_resources.sources import sources, source_for_url, publisher_resources


class PublisherSourceTests(unittest.TestCase):
    def setUp(self):
        self.store = ResourceMetadataStore()
        self.learner = Learner("source-browser", "unspecified")

    def tearDown(self):
        self.store.close()

    def test_official_snapshot_integrity_and_coverage(self):
        resources = publisher_resources()
        counts = {name: sum(r.provider == name for r in resources) for name in ("openstax", "nptel", "mit-ocw")}
        self.assertEqual(counts, {"openstax": 4790, "nptel": 3483, "mit-ocw": 744})
        self.assertEqual(len({r.url for r in resources}), 9017)
        self.assertTrue(all(r.reference_only and r.content is None and r.evidence for r in resources))
        self.assertTrue(all(r.availability == "unverified" and r.verified_at is None for r in resources))
        self.assertTrue(all(source_for_url(r.url) == r.provider for r in resources))

    def test_sitemap_labels_do_not_claim_page_titles_or_content(self):
        resources = publisher_resources()
        for resource in resources:
            if resource.provider != "nptel":
                self.assertEqual(resource.title_basis, "publisher_url_label")
                self.assertTrue(resource.title.startswith("Publisher URL label:"))
                self.assertIn("not a verified page heading", resource.evidence[0])

    def test_provider_filter_isolation(self):
        result = Orchestrator(self.store).references("linear algebra", self.learner, providers=["nptel"])
        self.assertEqual(result["status"], "references_found")
        self.assertTrue(all(r["resource"]["provider"] == "nptel" for r in result["references"]))
        self.assertTrue(all(r["provider"] == "nptel" for r in result["discovery_routes"]))
        self.assertTrue(all(r["resource"]["reference_kind"] == "course" for r in result["references"]))
        self.assertIn("choose the relevant chapter or lecture", result["references"][0]["activity"])

    def test_regional_language_portal_is_not_an_invented_lesson(self):
        result = Orchestrator(self.store).references("photosynthesis", replace(self.learner, language="hi"), providers=["diksha"])
        self.assertEqual(result["status"], "discovery_routes_available")
        self.assertEqual(result["references"], [])
        route = result["discovery_routes"][0]
        self.assertEqual(route["url"], "https://diksha.gov.in/explore")
        self.assertFalse(route["query_forwarded"])
        self.assertFalse(route["verified_lesson"])
        self.assertEqual(route["requested_language"], "hi")

    def test_ncert_and_swayam_are_honest_manual_routes(self):
        result = Orchestrator(self.store).references("some novel concept", self.learner, providers=["ncert", "swayam"])
        self.assertEqual(result["status"], "discovery_routes_available")
        self.assertEqual({r["provider"] for r in result["discovery_routes"]}, {"ncert", "swayam"})
        self.assertFalse(result["mastery_updated"])

    def test_source_domain_boundaries(self):
        self.assertEqual(source_for_url("https://archive.nptel.ac.in/lesson"), "nptel")
        self.assertIsNone(source_for_url("https://nptel.ac.in.example.org/lesson"))
        self.assertIsNone(source_for_url("https://evilnptel.ac.in/lesson"))

    def test_live_search_scoped_and_unrelated_results_rejected(self):
        seed = publisher_resources()[0]
        official = replace(seed, provider="web-references", url="https://ncert.nic.in/example", concepts=["search terms"], title="Bayes theorem")
        unrelated = replace(official, url="https://example.com/advertisement")
        provider = MagicMock()
        provider.search.return_value = [official, unrelated]
        service = ReferenceService(self.store, search_provider=provider, included_providers=["ncert"])
        result = service.search("Bayes theorem", self.learner, live=True)
        self.assertIn("site:ncert.nic.in", provider.search.call_args.args[0])
        self.assertEqual(result["total_matches"], 1)
        self.assertEqual(result["references"][0]["resource"]["provider"], "ncert")

    def test_checked_and_reviewed_metadata_survives_url_label_duplicate(self):
        base = next(r for r in publisher_resources() if r.provider == "openstax")
        reviewed = replace(base, title="Reviewed source title", title_basis="source_metadata", availability="verified", verified_at=now(), verification_evidence="Assessor inspected source")
        locator = replace(base, link_status="restricted", link_checked_at=now())
        service = ReferenceService(self.store, catalog=[reviewed, locator])
        result = service.search(base.concepts[0], self.learner, limit=1)
        item = result["references"][0]["resource"]
        self.assertEqual(item["title"], reviewed.title)
        self.assertEqual(item["availability"], "verified")
        self.assertEqual(item["link_status"], "restricted")

    def test_link_checks_bounded_to_returned_limit(self):
        metadata = publisher_resources()[:6]
        verifier = MagicMock(wraps=LinkVerifier(lambda url: 200))
        result = ReferenceService(self.store, catalog=metadata, verifier=verifier).search(metadata[0].concepts[0], self.learner, limit=2, check_links=True)
        self.assertGreaterEqual(result["total_matches"], 3)
        self.assertEqual(verifier.check.call_count, 2)

    def test_simple_question_matching_and_unknown_provider(self):
        engine = Orchestrator(self.store)
        result = engine.references("what is photosynthesis", self.learner, providers=["openstax"])
        self.assertEqual(result["status"], "references_found")
        self.assertIn("photosynthesis", result["references"][0]["resource"]["url"])
        with self.assertRaises(ValueError):
            engine.references("photosynthesis", self.learner, providers=["made-up"])

    def test_broad_course_not_used_as_targeted_intervention(self):
        engine = Orchestrator(self.store)
        seed = next(r for r in publisher_resources() if r.provider == "nptel")
        self.store.put(replace(seed, concepts=["torque"]))
        candidates = engine.discovery.discover("torque")
        self.assertFalse(any(r.reference_kind in {"course", "book", "catalog"} for r in candidates))

    def test_cli_source_listing(self):
        output = io.StringIO()
        with redirect_stdout(output):
            main(["--db", ":memory:", "sources"])
        self.assertEqual(len(json.loads(output.getvalue())), 10)
