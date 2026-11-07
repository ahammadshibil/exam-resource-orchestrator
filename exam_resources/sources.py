"""Official publisher indexes and explicit manual discovery routes."""
from importlib.resources import files
import json
from urllib.parse import urlsplit
from .models import Resource
from .references import canonical_link, reference_id


def sources():
    return json.loads(files("exam_resources").joinpath("data/sources.json").read_text(encoding="utf-8"))


def source_for_url(url, directories=None):
    host = urlsplit(canonical_link(url)).hostname
    for source in directories if directories is not None else sources():
        if any(host == domain or host.endswith("." + domain) for domain in source["domains"]):
            return source["id"]
    return None


def publisher_resources():
    directories = sources()
    path = files("exam_resources").joinpath("data/publisher_references.jsonl")
    result = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        metadata = json.loads(line)
        url = canonical_link(metadata["url"])
        if source_for_url(url, directories) != metadata["provider"]:
            raise ValueError("Publisher reference URL does not belong to its stated source")
        result.append(Resource(**metadata, id=reference_id(url), reference_only=True))
    return result


def discovery_routes(query, learner, included=(), excluded=()):
    directories = [s for s in sources() if s["id"] not in excluded and (not included or s["id"] in included)]
    if not included:
        preferred = ["ncert", "diksha", "swayam"] if learner.language not in {"en", "und"} else ["openstax", "nptel", "mit-ocw"]
        directories.sort(key=lambda s: preferred.index(s["id"]) if s["id"] in preferred else len(preferred))
        directories = directories[:3]
    return [{"provider": s["id"], "name": s["name"], "url": s["catalog_url"],
             "kind": "manual_catalog_route", "query": query, "requested_language": learner.language,
             "instruction": s["instruction"], "coverage": s["coverage"],
             "catalog_observation": s.get("catalog_observation", "Catalog navigation verified; individual lessons not inspected"),
             "query_forwarded": False, "verified_lesson": False,
             "note": "Open the catalog and search manually. This is not a topic-specific lesson or a claim that the requested language is available."}
            for s in directories]
