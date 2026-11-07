import io
import json
import os
from pathlib import Path
import tempfile
import unittest
from contextlib import redirect_stdout
from dataclasses import replace
from unittest.mock import patch, MagicMock
from urllib.error import HTTPError, URLError
from exam_resources import Orchestrator, Learner, ResourceMetadataStore
from exam_resources.cli import main
from exam_resources.references import ReferenceService, BraveReferenceSearch, LinkVerifier, canonical_link


class ReferenceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir=os.environ.get("EXAM_TEST_TMP"))
        self.path = str(Path(self.temp.name) / "references.sqlite3")
        self.store = ResourceMetadataStore(self.path)
        self.service = ReferenceService(self.store)
        self.learner = Learner("references", "unspecified")
        self.metadata = {"provider": "university", "title": "Eigenvalues and Eigenvectors",
                         "url": "https://ocw.mit.edu/example#lecture", "concepts": ["eigenvalues"],
                         "section": "Exact section unverified", "license": "Unknown", "language": "en"}

    def tearDown(self):
        self.store.close()
        self.temp.cleanup()

    def test_arbitrary_topic_reference_without_diagnostic(self):
        self.service.add(self.metadata)
        result = Orchestrator(self.store).references("eigenvalues", self.learner)
        self.assertEqual(result["status"], "references_found")
        self.assertFalse(result["reviewed_topic_available"])
        self.assertFalse(result["content_downloaded"])
        self.assertFalse(result["mastery_updated"])
        self.assertIn("Self-check only", result["references"][0]["assessment_status"])
        self.assertTrue(result["references"][0]["activity"])
        self.assertIsNone(self.store.get_mastery("references", "eigenvalues"))

    def test_unknown_permission_and_cost_do_not_hide_link(self):
        resource = self.service.add(self.metadata)
        item = self.service.search("eigenvalues", self.learner)["references"][0]
        self.assertEqual(item["resource"]["url"], resource.url)
        self.assertTrue(item["access_blocked_or_unknown"])
        self.assertIn("unknown cost", item["access_note"])
        self.assertEqual(item["resource"]["license"], "Unknown")
        self.assertIsNone(item["resource"]["content"])

    def test_restricted_and_dead_links_retained_with_labels(self):
        for code, expected in [(403, "restricted"), (404, "unavailable"), (451, "restricted"), (302, "redirect"), (405, "unknown")]:
            with self.subTest(code=code):
                resource = self.service.add(self.metadata)
                service = ReferenceService(self.store, verifier=LinkVerifier(lambda url: code))
                item = service.search("eigenvalues", self.learner, check_links=True)["references"][0]
                self.assertEqual(item["resource"]["link_status"], expected)
                self.assertEqual(item["resource"]["url"], resource.url)
                self.assertEqual(item["resource"]["availability"], "unverified")

    def test_head_success_does_not_verify_content_or_license(self):
        resource = self.service.add(self.metadata)
        checked = LinkVerifier(lambda url: 200).check(resource)
        self.assertEqual(checked.link_status, "reachable")
        self.assertEqual(checked.availability, "unverified")
        self.assertIsNone(checked.verified_at)
        self.assertIsNotNone(checked.link_checked_at)
        self.assertEqual(checked.license, "Unknown")

    def test_real_head_transport_never_reads_body_or_follows_redirect(self):
        response = MagicMock()
        response.__enter__.return_value.status = 200
        opener = MagicMock()
        opener.open.return_value = response
        with patch("exam_resources.references.socket.getaddrinfo", return_value=[(2, 1, 6, "", ("93.184.216.34", 443))]), patch("exam_resources.references.build_opener", return_value=opener):
            self.assertEqual(LinkVerifier._head("https://example.com/lesson"), 200)
        request = opener.open.call_args.args[0]
        self.assertEqual(request.get_method(), "HEAD")
        response.read.assert_not_called()
        response.__enter__.return_value.read.assert_not_called()

    def test_private_addresses_not_requested(self):
        for address in ["127.0.0.1", "10.0.0.1", "::1", "169.254.169.254"]:
            with self.subTest(address=address), patch("exam_resources.references.socket.getaddrinfo", return_value=[(2, 1, 6, "", (address, 443))]), patch("exam_resources.references.build_opener") as opener:
                with self.assertRaises(ValueError):
                    LinkVerifier._head("https://example.com/lesson")
                opener.assert_not_called()

    def test_http_exception_and_timeout_are_conservative(self):
        resource = self.service.add(self.metadata)
        def denied(url):
            raise HTTPError(url, 403, "Forbidden", {}, None)
        self.assertEqual(LinkVerifier(denied).check(resource).link_status, "restricted")
        def offline(url):
            raise URLError("network unavailable")
        self.assertEqual(LinkVerifier(offline).check(resource).link_status, "unknown")

    def test_forbidden_content_cannot_enter_reference_index(self):
        for change in ({"content": "copied chapter"}, {"offline": True}, {"id": "provided"}, {"reference_only": False}):
            with self.assertRaises(ValueError):
                self.service.add({**self.metadata, **change})
        with self.assertRaises(ValueError):
            replace(self.service.add(self.metadata), content="copied chapter")

    def test_dedup_and_reopen_persist_metadata(self):
        first = self.service.add(self.metadata)
        self.service.add({**self.metadata, "title": "Updated eigenvalues lesson"})
        self.store.close()
        self.store = ResourceMetadataStore(self.path)
        self.assertEqual(len(self.store.resources()), 1)
        self.assertEqual(self.store.resources()[0].id, first.id)
        self.assertEqual(self.store.resources()[0].title, "Updated eigenvalues lesson")

    def test_search_api_retains_only_metadata_not_snippets(self):
        calls = []
        def transport(url, headers):
            calls.append((url, headers))
            return {"web": {"results": [{"title": "Eigenvalues lesson", "url": self.metadata["url"],
                                          "description": "SNIPPET_NOT_STORED", "text": "CONTENT_NOT_STORED"},
                                         {"title": "Bad", "url": "javascript:alert(1)"}]}}
        provider = BraveReferenceSearch("secret", transport)
        service = ReferenceService(self.store, search_provider=provider)
        result = service.search("eigenvalues", self.learner, live=True)
        self.assertEqual(result["total_matches"], 1)
        self.assertIn("q=eigenvalues", calls[0][0])
        self.assertEqual(calls[0][1]["X-Subscription-Token"], "secret")
        serialized = json.dumps([r.__dict__ for r in self.store.resources()])
        self.assertNotIn("SNIPPET_NOT_STORED", serialized)
        self.assertNotIn("CONTENT_NOT_STORED", serialized)
        self.assertNotIn("secret", serialized)
        self.assertEqual(result["references"][0]["resource"]["language"], "und")

    def test_no_network_without_explicit_live_or_check(self):
        self.service.add(self.metadata)
        provider, verifier = MagicMock(), MagicMock()
        ReferenceService(self.store, search_provider=provider, verifier=verifier).search("eigenvalues", self.learner)
        provider.search.assert_not_called()
        verifier.check.assert_not_called()

    def test_offline_browse_never_checks_links(self):
        self.service.add(self.metadata)
        verifier = MagicMock()
        learner = replace(self.learner, online=False)
        result = ReferenceService(self.store, verifier=verifier).search("eigenvalues", learner, check_links=True)
        self.assertEqual(result["status"], "references_found")
        verifier.check.assert_not_called()
        with self.assertRaises(ValueError):
            self.service.search("eigenvalues", learner, live=True)

    def test_search_failure_falls_back_without_logging_token(self):
        self.service.add(self.metadata)
        provider = MagicMock()
        provider.search.side_effect = OSError("secret token in provider error")
        result = ReferenceService(self.store, search_provider=provider).search("eigenvalues", self.learner, live=True)
        self.assertEqual(result["status"], "references_found")
        self.assertNotIn("secret token", json.dumps(result))

    def test_missing_credentials_returns_explicit_fallback(self):
        self.service.add(self.metadata)
        result = self.service.search("eigenvalues", self.learner, live=True)
        self.assertEqual(result["status"], "references_found")
        self.assertTrue(result["errors"])

    def test_rank_usable_links_ahead_of_restricted_ones(self):
        self.service.add(self.metadata)
        self.service.add({**self.metadata, "url": "https://example.com/free", "cost": "free"})
        result = self.service.search("eigenvalues", self.learner)
        self.assertFalse(result["references"][0]["access_blocked_or_unknown"])
        self.assertTrue(result["references"][1]["access_blocked_or_unknown"])

    def test_imported_reference_available_to_reviewed_tutoring(self):
        self.service.add({**self.metadata, "concepts": ["torque"], "cost": "free"})
        engine = Orchestrator(self.store)
        candidates = engine.discovery.discover("torque")
        self.assertTrue(any(r.reference_only for r in candidates))

    def test_rediscovery_preserves_reviewed_metadata(self):
        resource = self.service.add({**self.metadata, "cost": "free"})
        provider = MagicMock()
        provider.search.return_value = [replace(resource, title="Search result title", concepts=["new alias"])]
        result = ReferenceService(self.store, search_provider=provider).search("new alias", self.learner, live=True)
        self.assertEqual(result["total_matches"], 1)
        self.assertEqual(self.store.resources()[0].title, resource.title)
        self.assertEqual(self.store.resources()[0].cost, "free")

    def test_url_query_and_section_preserved_and_unsafe_schemes_rejected(self):
        self.assertEqual(canonical_link("https://EXAMPLE.com/lesson?q=1#section"), "https://example.com/lesson?q=1#section")
        for url in ["http://example.com", "file:///etc/passwd", "https://user:pass@example.com", "https://example.com:8000"]:
            with self.assertRaises(ValueError):
                canonical_link(url)

    def test_cli_import_then_reference_unknown_topic(self):
        path = Path(self.temp.name) / "metadata.json"
        path.write_text(json.dumps(self.metadata), encoding="utf-8")
        with redirect_stdout(io.StringIO()):
            main(["--db", self.path, "add-reference", str(path)])
        output = io.StringIO()
        with redirect_stdout(output):
            main(["--db", self.path, "references", "eigenvalues"])
        self.assertEqual(json.loads(output.getvalue())["status"], "references_found")
