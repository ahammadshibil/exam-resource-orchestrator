from dataclasses import asdict
from datetime import datetime, timedelta, timezone
from importlib.resources import files
import json
import math
import uuid
from .models import Assessment, Gap, Learner, Prescription, Resource, now, unit
from .providers import CatalogAdapter, ProviderRegistry, GeminiNotebookAdapter
from .store import ResourceMetadataStore


def load_topics():
    return json.loads(files("exam_resources").joinpath("data/topics.json").read_text(encoding="utf-8"))


class ResourceDiscovery:
    def __init__(self, registry, store):
        self.registry, self.store = registry, store
        self.errors = []

    def discover(self, concept):
        self.errors = []
        found = {}
        for name, adapter in self.registry.adapters.items():
            try:
                for resource in adapter.discover(concept):
                    if resource.provider != name:
                        raise ValueError("Provider identity mismatch")
                    self.store.put(resource)
                    found[resource.id] = resource
            except (OSError, ValueError, TimeoutError) as error:
                self.errors.append({"provider": name, "error": type(error).__name__})
        return list(found.values())


class ResourceMatcher:
    @staticmethod
    def exclusion(resource, learner):
        if resource.availability == "unavailable":
            return "Provider unavailable"
        if not learner.online and not (resource.offline and resource.content):
            return "Requires internet or an authorized local copy"
        if resource.cost != "free" and not learner.allow_paid:
            return "Paid or unknown cost"
        if set(resource.requirements) - set(learner.entitlements):
            return "Missing access entitlement"
        if resource.countries and learner.country not in resource.countries:
            return "Region unsupported or unknown"
        if resource.blocked_countries and (learner.country is None or learner.country in resource.blocked_countries):
            return "Region restricted or unknown"
        if resource.min_age and (learner.age is None or learner.age < resource.min_age):
            return "Age eligibility not established"
        if set(resource.prerequisites) - set(learner.known):
            return "Prerequisites need assessment first"
        if set(learner.accessibility) - set(resource.accessibility):
            return "Accessibility needs not confirmed"
        if resource.minutes and resource.minutes > learner.minutes - 5:
            return "Insufficient time including assessment"
        return None


DEFAULT_WEIGHTS = {"concept": 5, "authority": 3, "exam_alignment": 3,
                   "prerequisites": 2, "quality": 1, "representation": 2,
                   "language_accessibility": 3, "time": 2, "cost": 1,
                   "availability": 2, "effectiveness": 1, "preference": .5,
                   "exploration": .5}


class RecommendationRanker:
    """Transparent policy scores, not empirical resource reviews."""
    def __init__(self, store, weights=None):
        self.store = store
        self.weights = dict(DEFAULT_WEIGHTS if weights is None else weights)
        if set(self.weights) != set(DEFAULT_WEIGHTS) or any(
                not isinstance(v, (int, float)) or not math.isfinite(v) or v < 0 for v in self.weights.values()
        ) or not sum(self.weights.values()):
            raise ValueError("Supply nonnegative finite rubric weights with all named factors")

    def score(self, resource, learner, gap):
        history = [h for h in self.store.history(learner.id, gap.concept) if h["resource"] == resource.id]
        gains, failed = [], False
        for item in history:
            assessments = [e["payload"] for e in self.store.events(item["id"]) if e["kind"] == "assessment"]
            if assessments:
                latest = assessments[-1]
                failed = failed or latest["score"] < .8
                if latest["gain"] is not None:
                    gains.append(latest["gain"])
        # Shrink sparse, confounded observations strongly toward neutral.
        effectiveness = .5 + sum(gains) / (10 + 2 * len(gains))
        if failed:
            effectiveness = min(effectiveness, .25)
        authoritative = resource.provider in {"openstax", "khan", "phet", "official", "ncert", "mit-ocw", "nptel"}
        verified = resource.availability == "verified"
        if verified:
            verified = datetime.now(timezone.utc) - datetime.fromisoformat(resource.verified_at) <= timedelta(days=30)
        factors = {
            "concept": float(gap.concept in resource.concepts),
            "authority": .9 if authoritative else .5,
            "exam_alignment": .9 if learner.curriculum in resource.curricula and resource.mapping_evidence != "Concept mapping only; exam alignment not verified" else .3,
            "prerequisites": 1., "quality": resource.quality if resource.quality is not None else .5,
            "representation": 1. if (gap.kind in {"recognition", "understanding"} and resource.format == "interactive") or (gap.kind in {"recall", "execution"} and resource.format == "exercise") else .6,
            "language_accessibility": 1. if resource.language == learner.language else .1,
            "time": min(1., (resource.minutes or 10) / max(1, learner.minutes - 5)) if learner.deeper else 1. - min(.8, (resource.minutes or 10) / (2 * learner.minutes)),
            "cost": 1. if resource.cost == "free" else .2,
            "availability": 1. if resource.offline and resource.content else .8 if verified else .1,
            "effectiveness": effectiveness,
            "preference": float(learner.preferred_provider == resource.provider),
            "exploration": 0. if history else 1.,
        }
        total = sum(factors[k] * w for k, w in self.weights.items()) / sum(self.weights.values())
        return round(total, 4), factors


class LearningPrescriptionGenerator:
    def generate(self, resource, learner, gap, topic, assessment, score, factors):
        localized = topic.get("translations", {}).get(learner.language)
        language_match = localized and resource.language == learner.language
        activity = localized["activity"] if language_match else topic["activity"]
        if resource.provider == "phet" and gap.concept == "torque":
            activity += " In Balancing Act, vary mass and distance one at a time; record each balance prediction before testing it."
        warning = []
        if resource.availability != "verified":
            warning.append("Unverified resource: confirm access and content before use.")
        elif not resource.offline and datetime.now(timezone.utc) - datetime.fromisoformat(resource.verified_at) > timedelta(days=30):
            warning.append("Verification older than 30 days; confirm availability.")
        if resource.language != learner.language:
            warning.append(f"Requested language {learner.language} unavailable; this resource is {resource.language}. No translation assumed.")
        return Prescription(resource, score, factors,
                            f"Addresses {gap.concept}: {gap.misconception}. Selected using the explicit rubric; effectiveness is observational.",
                            resource.section, activity, topic["focus"], gap.misconception,
                            topic["recall"], assessment.public(), min(resource.minutes or 10, learner.minutes - 5), " ".join(warning))


class ActivityTracker:
    def __init__(self, store):
        self.store = store

    def record(self, identifier, status, engagement=None):
        if status not in {"opened", "started", "completed", "abandoned"}:
            raise ValueError("Invalid completion state")
        if engagement is not None:
            unit(engagement)
        self.store.event(identifier, "activity", {"status": status, "engagement": engagement, "source": "learner_report"})


class OutcomeEvaluator:
    def __init__(self, store):
        self.store = store

    def evaluate(self, identifier, assessment_id, criteria, response, *, delayed=False, independent=False, assessor="learner"):
        record = self.store.intervention(identifier)
        specification = record["payload"]["assessment"]
        if assessment_id != specification["id"]:
            raise ValueError("Use the assigned independent assessment")
        if not independent or not response.strip():
            raise ValueError("An independent response is required; completion is insufficient")
        if len(criteria) != len(specification["rubric"]) or any(type(x) is not bool for x in criteria):
            raise ValueError("Submit one boolean per rubric criterion")
        if assessor not in {"learner", "tutor", "teacher"}:
            raise ValueError("Unknown assessor")
        if any(e["kind"] == "assessment" for e in self.store.events(identifier)):
            raise ValueError("Assessment already submitted; prescribe a new unseen assessment")
        if delayed and datetime.now(timezone.utc) - datetime.fromisoformat(record["created_at"]) < timedelta(hours=24):
            raise ValueError("Delayed retention requires at least 24 hours after prescription")
        score = sum(criteria) / len(criteria)
        baseline = record["payload"]["gap"]["baseline"]
        result = {"score": score, "gain": None if baseline is None else score - baseline,
                  "response": response, "criteria": criteria, "assessor": assessor,
                  "delayed": delayed, "confidence": "low: sparse, noncausal observation",
                  "next_strategy": "schedule_retention" if score >= .8 else "change_resource_and_rediagnose",
                  "causal_attribution": False, "assessed_at": now(), "intervention": identifier}
        with self.store.db:
            self.store.db.execute("INSERT INTO events(intervention,kind,payload,created_at) VALUES (?,?,?,?)",
                                  (identifier, "assessment", json.dumps(result), now()))
            prior = self.store.get_mastery(record["learner"], record["concept"]) or {}
            prior.update({"last_score": score, "status": "demonstrated_once" if score >= .8 else "needs_work",
                          "updated_at": now(), "assessor": assessor})
            if delayed:
                prior["retention_score"] = score
                prior["status"] = "retained_once" if score >= .8 else "needs_work"
            self.store.db.execute("INSERT OR REPLACE INTO mastery VALUES (?,?,?)",
                                  (record["learner"], record["concept"], json.dumps(prior)))
        return result


class Orchestrator:
    def __init__(self, store=None, registry=None, weights=None, topics=None):
        self.store = store or ResourceMetadataStore()
        self.topics = load_topics()
        if topics:
            self.topics.update(topics)
        self.registry = registry if registry is not None else self.default_registry()
        self.discovery = ResourceDiscovery(self.registry, self.store)
        self.ranker = RecommendationRanker(self.store, weights)
        self.tracker = ActivityTracker(self.store)
        self.evaluator = OutcomeEvaluator(self.store)

    @staticmethod
    def default_registry():
        registry = ProviderRegistry()
        resources = [Resource(**r) for r in json.loads(files("exam_resources").joinpath("data/catalog.json").read_text(encoding="utf-8"))]
        for provider in sorted({r.provider for r in resources}):
            registry.register(CatalogAdapter(provider, [r for r in resources if r.provider == provider]))
        # Empty optional categories are extension points, not invented lessons or API claims.
        for provider in ["official", "mit-ocw", "nptel", "swayam", "diksha", "ncert", "university", "youtube", "uploads"]:
            registry.register(CatalogAdapter(provider))
        registry.register(GeminiNotebookAdapter())
        return registry

    def diagnostic(self, concept):
        topic = self.topics.get(concept)
        if not topic:
            return {"concept": concept, "requires_authoring": True,
                    "instruction": "Supply syllabus outcomes, an authorized resource section and a teacher-authored diagnostic plus rubric. No knowledge gap inferred."}
        return {"concept": concept, "prompt": topic["diagnostic"]["prompt"],
                "criteria": topic["diagnostic"]["rubric"], "instruction": "Attempt before instruction; record response and tutor rubric marks."}

    def diagnose(self, concept, response, marks):
        topic = self.topics[concept]
        diagnostic = topic["diagnostic"]
        if not response.strip() or len(marks) != len(diagnostic["rubric"]) or any(type(x) is not bool for x in marks):
            raise ValueError("Diagnostic response and one boolean per criterion required")
        missing = [diagnostic["kinds"][i] for i, mark in enumerate(marks) if not mark]
        baseline = sum(marks) / len(marks)
        return Gap(concept, missing[0] if missing else "recall", topic["misconception"] if missing else "Check transfer and retention",
                   baseline, json.dumps({"response": response, "marks": marks, "basis": "explicit rubric; tutor or learner scored"}), True)

    def _assessment(self, learner, gap):
        seen = {h["payload"]["assessment"]["id"] for h in self.store.history(learner.id, gap.concept)}
        for item in self.topics[gap.concept]["assessments"]:
            if item["id"] not in seen:
                return Assessment(**item)
        return None

    def recommend(self, learner, gap, limit=2):
        if not 1 <= limit <= 3:
            raise ValueError("Recommend between one and three resources")
        if gap.concept not in self.topics or not gap.confirmed:
            return {"status": "diagnostic_required", "diagnostic": self.diagnostic(gap.concept), "recommendations": []}
        assessment = self._assessment(learner, gap)
        if assessment is None:
            return {"status": "assessment_authoring_required", "recommendations": [],
                    "instruction": "All independent questions have been used. Add a reviewed unseen assessment before continuing."}
        candidates = self.discovery.discover(gap.concept)
        eligible, excluded = [], []
        for resource in candidates:
            reason = ResourceMatcher.exclusion(resource, learner)
            if reason:
                excluded.append({"resource": resource.id, "reason": reason})
            else:
                score, factors = self.ranker.score(resource, learner, gap)
                eligible.append((score, resource, factors))
        # Respect requested language when supported, rather than silently translating.
        same_language = [x for x in eligible if x[1].language == learner.language]
        if same_language:
            eligible = same_language
        history = self.store.history(learner.id, gap.concept)
        if history:
            last = history[-1]
            outcomes = [e["payload"] for e in self.store.events(last["id"]) if e["kind"] == "assessment"]
            if outcomes and outcomes[-1]["score"] < .8:
                alternatives = [x for x in eligible if x[1].id != last["resource"]]
                if alternatives:
                    eligible = alternatives
        eligible.sort(key=lambda x: (-x[0], x[1].id))
        generator = LearningPrescriptionGenerator()
        prescriptions = [generator.generate(r, learner, gap, self.topics[gap.concept], assessment, s, f)
                         for s, r, f in eligible[:limit]]
        return {"status": "ready" if prescriptions else "no_eligible_resource",
                "recommendations": [p.to_dict() for p in prescriptions], "excluded": excluded,
                "provider_errors": self.discovery.errors,
                "assessment_id": assessment.id, "diagnosis": asdict(gap)}

    def start(self, learner, gap, resource_id=None):
        result = self.recommend(learner, gap, limit=3)
        if result["status"] != "ready":
            return result
        options = result["recommendations"]
        chosen = options[0] if resource_id is None else next((x for x in options if x["resource"]["id"] == resource_id), None)
        if chosen is None:
            raise ValueError("Choose a currently eligible recommended resource")
        assessment = self._assessment(learner, gap)
        identifier = str(uuid.uuid4())
        prescription = Prescription(**{**chosen, "resource": Resource(**chosen["resource"])})
        self.store.start(identifier, learner, gap, prescription, assessment)
        return {"status": "started", "intervention": identifier, "prescription": chosen}

    def study_plan(self, learner, gaps, start_date, exam_date=None, daily_minutes=30):
        if daily_minutes < 10:
            raise ValueError("Daily budget must allow instruction and assessment")
        start = datetime.fromisoformat(start_date).date()
        exam = datetime.fromisoformat(exam_date).date() if exam_date else None
        sessions, pending, revisions = [], [], []
        used_minutes = {}
        ordered = sorted(gaps, key=lambda g: (g.baseline if g.baseline is not None else -1, g.concept))
        for index, gap in enumerate(ordered):
            day = start + timedelta(days=index)
            if exam and day > exam:
                pending.append({"concept": gap.concept, "reason": "No study day before exam"})
                continue
            session_learner = Learner(**{**asdict(learner), "minutes": min(learner.minutes, daily_minutes)})
            result = self.recommend(session_learner, gap)
            if result["status"] != "ready":
                pending.append({"concept": gap.concept, "reason": result["status"], "next": result.get("diagnostic")})
                continue
            primary = result["recommendations"][0]
            # Always seek a locally usable fallback, independently of provider ranking.
            fallback_learner = Learner(**{**asdict(session_learner), "online": False})
            fallback = self.recommend(fallback_learner, gap, limit=1)["recommendations"]
            revision_days = [day + timedelta(days=d) for d in (1, 7)]
            used_minutes[day] = primary["timebox_minutes"] + 5
            sessions.append({"date": day.isoformat(), "objective": gap.concept, "primary": primary,
                             "activity": primary["activity"], "active_recall": primary["recall"],
                             "assessment": primary["assessment"], "minutes": primary["timebox_minutes"] + 5,
                             "revision_dates": [],
                             "fallback": fallback[0] if fallback else None})
            revisions.extend((d, gap.concept, len(sessions) - 1) for d in revision_days if exam is None or d <= exam)
        revision_sessions = []
        for requested, concept, index in sorted(revisions):
            day = requested
            while used_minutes.get(day, 0) + 5 > daily_minutes:
                day += timedelta(days=1)
            if exam and day > exam:
                pending.append({"concept": concept, "reason": "Revision cannot fit before exam"})
                continue
            used_minutes[day] = used_minutes.get(day, 0) + 5
            sessions[index]["revision_dates"].append(day.isoformat())
            revision_sessions.append({"date": day.isoformat(), "objective": concept, "minutes": 5,
                                      "activity": "Closed-book recall, then obtain an unused assessment. Do not repeat a seen question as retention evidence."})
        return {"sessions": sessions, "pending": pending, "daily_minutes": daily_minutes,
                "revision_sessions": revision_sessions,
                "coverage": {"planned": len(sessions), "requested": len(gaps)},
                "note": "Includes five assessment minutes per teaching session and five minutes per revision. Unknown gaps require diagnostics first."}
