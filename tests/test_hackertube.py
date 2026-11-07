import json
import unittest
from dataclasses import asdict
from exam_resources import HackerTubeAdapter, Learner, Orchestrator, ResourceMetadataStore


class HackerTubeTests(unittest.TestCase):
    def record(self, **changes):
        return {"vid": "fNk_zzaMoSs", "url": "https://www.youtube.com/watch?v=fNk_zzaMoSs",
                "title": "Vectors | Chapter 1, Essence of linear algebra", "channel": "3Blue1Brown",
                "primary_topic": "linear algebra", "tags": ["vectors", "visual intuition"],
                "score": 1000000, "hn": {"mentions": 99999}, "summary": "SUMMARY_NOT_IMPORTED", **changes}

    def test_real_bundled_catalog_loaded_and_attributed(self):
        adapter = HackerTubeAdapter()
        self.assertEqual(len(adapter.resources), 6454)
        self.assertEqual(adapter.rejected_records, 0)
        self.assertTrue(adapter.discover("linear algebra"))
        first = adapter.resources[0]
        self.assertTrue(first.reference_only)
        self.assertEqual(first.format, "video")
        self.assertEqual(first.language, "und")
        self.assertIsNone(first.content)
        self.assertIsNone(first.minutes)
        self.assertIsNone(first.quality)
        self.assertIn("metadata only", first.license)
        self.assertIn("open-index/hacker-news", " ".join(first.evidence))

    def test_hn_popularity_and_summaries_not_used(self):
        first = HackerTubeAdapter([self.record()]).resources[0]
        second = HackerTubeAdapter([self.record(score=0, hn={"mentions": 0})]).resources[0]
        self.assertEqual(asdict(first), asdict(second))
        self.assertNotIn("SUMMARY_NOT_IMPORTED", json.dumps(asdict(first)))
        self.assertNotIn("1000000", json.dumps(asdict(first)))

    def test_invalid_records_rejected_without_making_up_urls(self):
        adapter = HackerTubeAdapter([
            self.record(vid="bad"), self.record(url="https://example.com/video"),
            self.record(url="https://www.youtube.com/watch?v=AAAAAAAAAAA"),
            self.record(title=""), self.record(tags="not a list")])
        self.assertEqual(adapter.resources, [])
        self.assertEqual(adapter.rejected_records, 5)

    def test_provider_optional_and_reference_query_works_without_keys(self):
        store = ResourceMetadataStore()
        try:
            engine = Orchestrator(store)
            learner = Learner("browser", "unspecified")
            result = engine.references("linear algebra", learner)
            self.assertEqual(result["status"], "references_found")
            self.assertTrue(any(item["resource"]["provider"] == "hackertube" for item in result["references"]))
            self.assertFalse(result["content_downloaded"])
            self.assertFalse(result["mastery_updated"])
            # A remembered link must not silently reactivate a removed provider.
            store.put(engine.registry.adapters["hackertube"].resources[0])
            engine.registry.remove("hackertube")
            result = engine.references("linear algebra", learner)
            self.assertFalse(any(item["resource"]["provider"] == "hackertube" for item in result["references"]))
        finally:
            store.close()
