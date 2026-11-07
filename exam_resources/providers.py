"""Adapters search authorized metadata, never scrape provider content."""
import json
import re
from typing import Protocol
from urllib.request import Request, urlopen
from urllib.parse import urlsplit
from .models import Resource


class ProviderAdapter(Protocol):
    id: str
    capabilities: dict[str, str]

    def discover(self, concept: str) -> list[Resource]: ...


class CatalogAdapter:
    def __init__(self, identifier, resources=(), capabilities=None):
        self.id = identifier
        self.resources = list(resources)
        if any(r.provider != identifier for r in self.resources):
            raise ValueError("Catalog resources must belong to their adapter")
        self.capabilities = capabilities or {"discovery": "local_metadata", "search": "local_metadata", "deep_links": "manual"}

    def discover(self, concept):
        return [r for r in self.resources if concept in r.concepts]


class ProviderRegistry:
    def __init__(self):
        self.adapters = {}
        self.disabled = set()

    def register(self, adapter):
        if adapter.id in self.adapters:
            raise ValueError(f"Provider already registered: {adapter.id}")
        self.adapters[adapter.id] = adapter
        self.disabled.discard(adapter.id)

    def remove(self, identifier):
        self.adapters.pop(identifier, None)
        self.disabled.add(identifier)

    def describe(self):
        return {key: adapter.capabilities for key, adapter in self.adapters.items()}


class GeminiNotebookAdapter(CatalogAdapter):
    """Official personal-account preview API; disabled unless explicitly configured.

    Documentation checked 2026-11-06: https://developers.google.com/notebook/docs
    This is not the distinct Enterprise discoveryengine API.
    """
    API = "https://notebook.googleapis.com/v1"

    def __init__(self, token=None, project=None, transport=None):
        super().__init__("gemini-notebook", capabilities={
            "create_notebook": "official_api_opt_in", "add_source": "official_api_opt_in",
            "deep_links": "manual", "source_grounded_study": "manual",
            "audio": "manual", "video": "manual", "mind_maps": "manual",
            "flashcards": "manual", "quizzes": "manual", "progress_exchange": "unsupported"})
        self.token, self.project = token, project
        self.transport = transport or self._http

    @staticmethod
    def _http(url, headers, payload):
        request = Request(url, data=json.dumps(payload).encode(), headers=headers, method="POST")
        with urlopen(request, timeout=20) as response:
            return json.load(response)

    def _post(self, path, payload):
        if not self.token or not self.project:
            raise PermissionError("Configure a scoped OAuth token and Google Cloud project first")
        return self.transport(self.API + path, {"Authorization": "Bearer " + self.token,
                              "x-goog-user-project": self.project, "Content-Type": "application/json"}, payload)

    def create_notebook(self, title, *, authorized=False):
        if not authorized:
            raise PermissionError("Explicit authorization to create an external notebook required")
        return self._post("/notebooks", {"display_name": title})

    def add_source(self, notebook, title, *, url=None, text=None, authorized=False, rights_confirmed=False):
        if not authorized or not rights_confirmed:
            raise PermissionError("Explicit external upload authorization and source rights confirmation required")
        if not re.fullmatch(r"notebooks/[A-Za-z0-9_-]+", notebook):
            raise ValueError("Expected notebooks/{id}")
        if (url is None) == (text is None):
            raise ValueError("Supply exactly one source URL or text")
        if url:
            p = urlsplit(url)
            if p.scheme != "https" or not p.hostname or p.username or p.password:
                raise ValueError("Source must use an HTTPS URL without credentials")
        payload = {"display_name": title}
        payload.update({"web_content": {"url": url}} if url else {"text_content": {"content": text}})
        return self._post("/" + notebook + "/sources", payload)

    @staticmethod
    def workflow(unit):
        return [f"Create a notebook named {unit}; group source titles by syllabus unit.",
                "Add only sources you are authorized to share. Keep learner records local.",
                "Ask a question grounded in those sources and check its citations.",
                "If available in your account, select audio, video, mind maps or quizzes in the provider UI.",
                "Return to Exam Reverse Engineer for an independent assessment."]
