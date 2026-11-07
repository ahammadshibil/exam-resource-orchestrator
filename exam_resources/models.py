from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from urllib.parse import urlsplit
import math


def now():
    return datetime.now(timezone.utc).isoformat()


def unit(value):
    if not isinstance(value, (int, float)) or not math.isfinite(value) or not 0 <= value <= 1:
        raise ValueError("Performance and scores must be finite numbers in [0, 1]")
    return value


@dataclass
class Resource:
    id: str
    provider: str
    title: str
    concepts: list[str]
    section: str
    url: str | None = None
    publisher: str = "Unknown"
    subject: str = ""
    curricula: list[str] = field(default_factory=list)
    mapping_evidence: str = "Concept mapping only; exam alignment not verified"
    prerequisites: list[str] = field(default_factory=list)
    level: str = "general"
    format: str = "text"
    language: str = "en"
    minutes: int | None = None
    duration_basis: str = "Unknown; use a learner timebox"
    cost: str = "unknown"
    requirements: list[str] = field(default_factory=list)
    countries: list[str] = field(default_factory=list)
    blocked_countries: list[str] = field(default_factory=list)
    min_age: int | None = None
    offline: bool = False
    availability: str = "unverified"
    verified_at: str | None = None
    verification_evidence: str = ""
    license: str = "Unknown; link only"
    permitted_usage: str = "Link only; no retrieval or redistribution"
    evidence: list[str] = field(default_factory=list)
    quality: float | None = None
    quality_basis: str = "No review score supplied"
    outcomes: list[str] = field(default_factory=list)
    accessibility: list[str] = field(default_factory=list)
    content: str | None = None
    reference_only: bool = False
    link_status: str = "unchecked"
    link_checked_at: str | None = None
    title_basis: str = "source_metadata"
    reference_kind: str = "resource"

    def __post_init__(self):
        if not self.id or not self.provider or not self.concepts or not self.section:
            raise ValueError("Resource needs identity, provider, concepts and a section")
        if self.url:
            p = urlsplit(self.url)
            if p.scheme != "https" or not p.hostname or p.username or p.password:
                raise ValueError("External resource links must be HTTPS URLs")
        if self.availability not in {"verified", "unverified", "unavailable"}:
            raise ValueError("Invalid availability")
        if self.availability == "verified" and not (self.verified_at and self.verification_evidence):
            raise ValueError("Verified resources need a timestamp and evidence")
        if self.verified_at:
            timestamp = datetime.fromisoformat(self.verified_at)
            if timestamp.tzinfo is None:
                raise ValueError("Verification timestamp must include timezone")
        if self.quality is not None:
            unit(self.quality)
        if self.minutes is not None and self.minutes <= 0:
            raise ValueError("Duration must be positive")
        if self.reference_only and (not self.url or self.content is not None or self.offline):
            raise ValueError("Link-only references need a URL and cannot contain downloaded content")
        if self.link_status not in {"unchecked", "reachable", "restricted", "unavailable", "redirect", "unknown"}:
            raise ValueError("Invalid link status")
        if self.title_basis not in {"source_metadata", "publisher_url_label"}:
            raise ValueError("Invalid title basis")
        if self.reference_kind not in {"resource", "lesson", "section", "course", "book", "catalog"}:
            raise ValueError("Invalid reference kind")


@dataclass
class Learner:
    id: str
    curriculum: str
    language: str = "en"
    country: str | None = None
    age: int | None = None
    online: bool = True
    allow_paid: bool = False
    entitlements: list[str] = field(default_factory=list)
    known: list[str] = field(default_factory=list)
    accessibility: list[str] = field(default_factory=list)
    preferred_provider: str | None = None
    deeper: bool = False
    minutes: int = 25

    def __post_init__(self):
        if not self.id or self.minutes < 10:
            raise ValueError("Learner ID and at least ten study minutes required")


@dataclass
class Gap:
    concept: str
    kind: str
    misconception: str
    baseline: float | None
    evidence: str
    confirmed: bool = False

    def __post_init__(self):
        if self.kind not in {"understanding", "recognition", "execution", "recall", "unknown"}:
            raise ValueError("Unknown gap kind")
        if self.baseline is not None:
            unit(self.baseline)
        if self.confirmed and (not self.evidence or self.baseline is None):
            raise ValueError("Confirmed gaps need diagnostic evidence and a baseline")


@dataclass
class Assessment:
    id: str
    prompt: str
    answer: str
    rubric: list[str]

    def public(self):
        return {"id": self.id, "prompt": self.prompt, "success": f"Satisfy all {len(self.rubric)} rubric criteria without hints"}


@dataclass
class Prescription:
    resource: Resource
    score: float
    factors: dict
    reason: str
    section: str
    activity: str
    focus: str
    misconception: str
    recall: str
    assessment: dict
    timebox_minutes: int
    warning: str = ""

    def to_dict(self):
        return asdict(self)
