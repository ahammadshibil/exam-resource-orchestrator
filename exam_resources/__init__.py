"""Resource orchestration; no provider, network connection or model is mandatory."""
from .models import Resource, Learner, Gap, Assessment, Prescription
from .providers import ProviderRegistry, CatalogAdapter, GeminiNotebookAdapter
from .engine import Orchestrator, ResourceDiscovery, ResourceMatcher, RecommendationRanker
from .engine import LearningPrescriptionGenerator, OutcomeEvaluator, ActivityTracker
from .store import ResourceMetadataStore
from .references import ReferenceService, BraveReferenceSearch, LinkVerifier

__all__ = ["Resource", "Learner", "Gap", "Assessment", "Prescription",
           "ProviderRegistry", "CatalogAdapter", "GeminiNotebookAdapter", "Orchestrator",
           "ResourceDiscovery", "ResourceMatcher", "RecommendationRanker",
           "LearningPrescriptionGenerator", "OutcomeEvaluator", "ActivityTracker",
           "ResourceMetadataStore", "ReferenceService", "BraveReferenceSearch", "LinkVerifier"]
