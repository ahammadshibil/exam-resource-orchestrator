import io
import json
import os
import tempfile
import unittest
from contextlib import redirect_stdout
from dataclasses import replace
from pathlib import Path
from unittest.mock import patch
from exam_resources import Orchestrator, Learner, Gap, ResourceMetadataStore
from exam_resources.providers import CatalogAdapter, GeminiNotebookAdapter, ProviderRegistry
from exam_resources.engine import RecommendationRanker, DEFAULT_WEIGHTS
from exam_resources.cli import main


class OrchestrationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir=os.environ.get("EXAM_TEST_TMP"))
        self.path = str(Path(self.temp.name) / "progress.sqlite3")
        self.store = ResourceMetadataStore(self.path)
        self.engine = Orchestrator(self.store)

    def tearDown(self):
        self.store.close()
        self.temp.cleanup()

    def gap(self, concept="torque"):
        return self.engine.diagnose(concept, "Incorrect attempt; assumes magnitude alone determines result", [False, False, True])

    def learner(self, **kwargs):
        return Learner("learner-1", "JEE", **kwargs)

    def verify_scenario(self, learner, gap):
        result = self.engine.start(learner, gap)
        self.assertEqual(result["status"], "started")
        prescription = result["prescription"]
        self.assertIn(gap.concept, prescription["resource"]["concepts"])
        for field in ("section", "activity", "focus", "recall", "assessment", "reason"):
            self.assertTrue(prescription[field])
        identifier = result["intervention"]
        self.engine.tracker.record(identifier, "completed", .8)
        self.assertIsNone(self.store.get_mastery(learner.id, gap.concept))
        assessment = prescription["assessment"]
        self.assertNotIn("answer", assessment)
        outcome = self.engine.evaluator.evaluate(identifier, assessment["id"], [True]*3,
                                                 "Independent worked response, teacher reviewed", independent=True, assessor="teacher")
        self.assertFalse(outcome["causal_attribution"])
        self.store.close()
        self.store = ResourceMetadataStore(self.path)
        self.engine = Orchestrator(self.store)
        self.assertEqual(self.store.get_mastery(learner.id, gap.concept)["last_score"], 1)
        self.assertEqual(len(self.store.events(identifier)), 2)
        return prescription

    def test_A_jee_torque_recognition(self):
        gap = self.gap()
        self.assertEqual(gap.kind, "recognition")
        self.verify_scenario(self.learner(), gap)

    def test_B_neet_mitosis_meiosis(self):
        gap = self.gap("cell-division")
        self.assertEqual(gap.kind, "recognition")
        p = self.verify_scenario(Learner("neet", "NEET"), gap)
        self.assertIn("homologous", p["activity"])

    def test_C_university_test_selection(self):
        p = self.verify_scenario(Learner("stats", "university-statistics"), self.gap("test-selection"))
        self.assertIn("sampling unit", p["activity"])

    def test_D_syllabus_without_papers(self):
        unknown = Gap("torque", "unknown", "Not assessed", None, "Syllabus only")
        result = self.engine.recommend(self.learner(), unknown)
        self.assertEqual(result["status"], "diagnostic_required")
        self.assertIn("prompt", result["diagnostic"])
        self.verify_scenario(self.learner(), self.gap())

    def test_E_no_internet(self):
        p = self.verify_scenario(self.learner(online=False), self.gap())
        self.assertTrue(p["resource"]["offline"])
        self.assertTrue(p["resource"]["content"])
        self.assertIsNone(p["resource"]["url"])
        self.assertNotIn("simulation", p["activity"])

    def test_F_paid_or_region_restricted_preference(self):
        seed = self.engine.discovery.discover("torque")[0]
        restricted = [replace(seed, id="paid", provider="preferred", cost="paid"),
                      replace(seed, id="blocked", provider="preferred", blocked_countries=["IN"])]
        self.engine.registry.register(CatalogAdapter("preferred", restricted))
        learner = self.learner(country="IN", preferred_provider="preferred")
        result = self.engine.recommend(learner, self.gap())
        self.assertEqual({x["resource"] for x in result["excluded"]} & {"paid", "blocked"}, {"paid", "blocked"})
        self.verify_scenario(learner, self.gap())

    def test_G_regional_language(self):
        p = self.verify_scenario(self.learner(language="hi"), self.gap())
        self.assertEqual(p["resource"]["language"], "hi")
        self.assertIn("धुरी", p["activity"])

    def test_unknown_language_is_explicit(self):
        result = self.engine.recommend(self.learner(language="ml"), self.gap())
        self.assertIn("Requested language ml unavailable", result["recommendations"][0]["warning"])

    def test_provider_failure_and_removal(self):
        class Broken:
            id = "broken"
            capabilities = {}
            def discover(self, concept):
                raise OSError("provider down")
        self.engine.registry.register(Broken())
        self.engine.registry.remove("openstax")
        result = self.engine.recommend(self.learner(online=False), self.gap())
        self.assertEqual(result["status"], "ready")
        self.assertEqual(result["provider_errors"][0]["provider"], "broken")
        self.assertFalse(any(r["resource"]["provider"] == "openstax" for r in result["recommendations"]))

    def test_empty_registry_is_respected(self):
        engine = Orchestrator(self.store, ProviderRegistry())
        self.assertEqual(engine.recommend(self.learner(), self.gap())["status"], "no_eligible_resource")

    def test_no_assessment_reuse_and_strategy_changes(self):
        learner, gap = self.learner(), self.gap()
        first = self.engine.start(learner, gap)
        self.engine.evaluator.evaluate(first["intervention"], first["prescription"]["assessment"]["id"],
                                       [False]*3, "Still incorrect", independent=True)
        second = self.engine.start(learner, gap)
        self.assertNotEqual(first["prescription"]["resource"]["id"], second["prescription"]["resource"]["id"])
        self.assertNotEqual(first["prescription"]["assessment"]["id"], second["prescription"]["assessment"]["id"])
        self.engine.start(learner, gap)
        self.assertEqual(self.engine.start(learner, gap)["status"], "assessment_authoring_required")

    def test_assessment_validation(self):
        first = self.engine.start(self.learner(), self.gap())
        identifier, aid = first["intervention"], first["prescription"]["assessment"]["id"]
        for kwargs in ({"independent": False}, {"independent": True, "delayed": True}):
            with self.assertRaises(ValueError):
                self.engine.evaluator.evaluate(identifier, aid, [True]*3, "Attempt", **kwargs)
        with self.assertRaises(ValueError):
            self.engine.evaluator.evaluate(identifier, "wrong", [True]*3, "Attempt", independent=True)
        self.engine.evaluator.evaluate(identifier, aid, [True]*3, "Attempt", independent=True)
        with self.assertRaises(ValueError):
            self.engine.evaluator.evaluate(identifier, aid, [True]*3, "Attempt", independent=True)

    def test_delayed_retention_persisted(self):
        item = self.engine.start(self.learner(), self.gap())
        with self.store.db:
            self.store.db.execute("UPDATE interventions SET created_at=? WHERE id=?", ("2020-01-01T00:00:00+00:00", item["intervention"]))
        self.engine.evaluator.evaluate(item["intervention"], item["prescription"]["assessment"]["id"],
                                       [True]*3, "Delayed unseen answer", independent=True, delayed=True)
        self.assertEqual(self.store.get_mastery("learner-1", "torque")["retention_score"], 1)

    def test_access_guards(self):
        from exam_resources.engine import ResourceMatcher
        seed = self.engine.discovery.discover("torque")[0]
        for change in ({"requirements": ["subscription"]}, {"min_age": 18}, {"countries": ["US"]},
                       {"prerequisites": ["calculus"]}, {"minutes": 100}, {"availability": "unavailable"}):
            self.assertIsNotNone(ResourceMatcher.exclusion(replace(seed, **change), self.learner()))

    def test_metadata_and_ranking_validation(self):
        seed = self.engine.discovery.discover("torque")[0]
        for change in ({"url": "javascript:alert(1)"}, {"quality": float("nan")},
                       {"availability": "verified", "verified_at": None}):
            with self.assertRaises(ValueError):
                replace(seed, **change)
        with self.assertRaises(ValueError):
            RecommendationRanker(self.store, {**DEFAULT_WEIGHTS, "concept": -1})
        with self.assertRaises(ValueError):
            Gap("torque", "recall", "", float("nan"), "")

    def test_plan_budgets_exam_and_fallback(self):
        gaps = [self.gap(c) for c in ("torque", "cell-division", "test-selection")]
        plan = self.engine.study_plan(self.learner(), gaps, "2026-11-06", "2026-11-15", daily_minutes=15)
        spent = {}
        for session in plan["sessions"] + plan["revision_sessions"]:
            spent[session["date"]] = spent.get(session["date"], 0) + session["minutes"]
            self.assertLessEqual(session["date"], "2026-11-15")
        self.assertTrue(all(n <= 15 for n in spent.values()))
        self.assertTrue(all(s["fallback"]["resource"]["offline"] for s in plan["sessions"]))
        self.assertEqual(plan["coverage"]["planned"], 3)

    def test_unknown_syllabus_concept_does_not_invent_material(self):
        result = self.engine.recommend(self.learner(), Gap("unknown", "unknown", "", None, "syllabus"))
        self.assertTrue(result["diagnostic"]["requires_authoring"])

    def test_notebook_authorization_and_exact_requests(self):
        calls = []
        def transport(url, headers, payload):
            calls.append((url, headers, payload))
            return {"name": "notebooks/abc"}
        adapter = GeminiNotebookAdapter("scoped-token", "project", transport)
        with self.assertRaises(PermissionError):
            adapter.create_notebook("Physics")
        with self.assertRaises(PermissionError):
            adapter.add_source("notebooks/abc", "Private", text="notes", authorized=True)
        self.assertEqual(calls, [])
        adapter.create_notebook("Physics", authorized=True)
        adapter.add_source("notebooks/abc", "Unit 1", text="owned notes", authorized=True, rights_confirmed=True)
        self.assertEqual(calls[0][0], "https://notebook.googleapis.com/v1/notebooks")
        self.assertEqual(calls[0][2], {"display_name": "Physics"})
        self.assertEqual(calls[1][2]["text_content"]["content"], "owned notes")
        self.assertNotIn("progress", json.dumps(calls))

    def test_cli_end_to_end(self):
        request = Path(self.temp.name) / "request.json"
        from dataclasses import asdict
        request.write_text(json.dumps({"learner": asdict(self.learner()), "gap": asdict(self.gap())}), encoding="utf-8")
        output = io.StringIO()
        with redirect_stdout(output):
            main(["--db", self.path, "start", str(request)])
        item = json.loads(output.getvalue())
        self.assertEqual(item["status"], "started")
        with redirect_stdout(io.StringIO()):
            main(["--db", self.path, "activity", item["intervention"], "completed"])
        self.assertIsNone(self.store.get_mastery("learner-1", "torque"))


if __name__ == "__main__":
    unittest.main()
