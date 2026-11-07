"""HackerTube's attributed public reference catalog; no video content or HN scores."""
from importlib.resources import files
import json
import re
from urllib.parse import parse_qs, urlsplit
from .models import Resource
from .providers import CatalogAdapter
from .references import reference_id, tokens


class HackerTubeAdapter(CatalogAdapter):
    def __init__(self, records=None):
        if records is None:
            text = files("exam_resources").joinpath("data/hackertube.jsonl").read_text(encoding="utf-8")
            records = [json.loads(line) for line in text.splitlines() if line.strip()]
        resources = {}
        self.rejected_records = 0
        for record in records:
            try:
                video_id = record["vid"]
                if not isinstance(video_id, str) or not re.fullmatch(r"[A-Za-z0-9_-]{11}", video_id):
                    raise ValueError("Invalid YouTube ID")
                parts = urlsplit(record["url"])
                if parts.scheme != "https" or parts.hostname != "www.youtube.com" or parts.path != "/watch" or parse_qs(parts.query).get("v") != [video_id]:
                    raise ValueError("Exported URL does not match the video ID")
                title = record["title"].strip()
                if not title:
                    raise ValueError("Empty catalog title")
                tags = record.get("tags", [])
                if not isinstance(tags, list) or any(not isinstance(tag, str) for tag in tags):
                    raise ValueError("Invalid topic tags")
                concepts = list(dict.fromkeys([tag.strip() for tag in [record.get("primary_topic", ""), *tags] if tag.strip()]))
                if not concepts:
                    concepts = [title]
                resource = Resource(
                    id=reference_id(record["url"]), provider="hackertube", title=title, url=record["url"],
                    publisher=record.get("channel") or "Unknown", concepts=concepts, format="video", language="und",
                    section="Exact segment and timestamps not verified; locate the requested topic in the original video",
                    reference_only=True, availability="unverified", cost="unknown",
                    mapping_evidence="HackerTube topic labels; independent concept and exam alignment checks pending",
                    license="ODC-By-1.0 (https://opendatacommons.org/licenses/by/1-0/) for catalog metadata only; video rights are separate",
                    permitted_usage="Original-video link and attributed catalog metadata; no video or transcript copying assumed",
                    evidence=["Reference metadata: HackerTube (https://hackertube.org/data), derived from open-index/hacker-news (https://huggingface.co/datasets/open-index/hacker-news).",
                              f"Catalog entry: https://hackertube.org/watch/{video_id}. Video playback, language, access and instructional accuracy unverified."])
                resources[resource.id] = resource
            except (KeyError, TypeError, ValueError, AttributeError):
                self.rejected_records += 1
        super().__init__("hackertube", resources.values(), capabilities={
            "discovery": "attributed_public_export", "search": "local_metadata",
            "deep_links": "manual", "content_retrieval": "unsupported", "progress_exchange": "unsupported"})

    def discover(self, concept):
        wanted = tokens(concept)
        return [resource for resource in self.resources if wanted and wanted.issubset(
            tokens(" ".join([resource.title, *resource.concepts])))]
