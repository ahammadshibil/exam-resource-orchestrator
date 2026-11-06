"""JSON input/output CLI suitable for Codex conversational orchestration."""
import argparse
import json
from pathlib import Path
from .engine import Orchestrator
from .models import Gap, Learner, Resource
from .providers import CatalogAdapter
from .store import ResourceMetadataStore


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", default="learning.sqlite3", help="Local SQLite file")
    parser.add_argument("--catalog", help="Additional authorized metadata resources as a JSON array")
    parser.add_argument("--weights", help="JSON file containing every ranking weight")
    parser.add_argument("--topics", help="JSON concept definitions with diagnostics and unseen assessments")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("providers")
    diagnostic = sub.add_parser("diagnostic")
    diagnostic.add_argument("concept")
    diagnose = sub.add_parser("diagnose")
    diagnose.add_argument("input", help="JSON: concept, response and boolean marks")
    for command in ("recommend", "start", "plan"):
        command_parser = sub.add_parser(command)
        command_parser.add_argument("input", help="JSON request file")
    activity = sub.add_parser("activity")
    activity.add_argument("intervention")
    activity.add_argument("status", choices=["opened", "started", "completed", "abandoned"])
    assess = sub.add_parser("assess")
    assess.add_argument("input", help="JSON evaluator arguments including criteria, response, independent and assessor")
    rubric = sub.add_parser("rubric", help="Assessor view; only reveal after the learner responds")
    rubric.add_argument("intervention")
    history = sub.add_parser("history")
    history.add_argument("learner")
    history.add_argument("--concept")
    mastery = sub.add_parser("mastery")
    mastery.add_argument("learner")
    mastery.add_argument("concept")
    args = parser.parse_args(argv)
    store = ResourceMetadataStore(args.db)
    try:
        engine = Orchestrator(store, weights=read(args.weights) if args.weights else None,
                              topics=read(args.topics) if args.topics else None)
        if args.catalog:
            resources = [Resource(**item) for item in read(args.catalog)]
            for provider in sorted({r.provider for r in resources}):
                existing = engine.registry.adapters.get(provider)
                previous = existing.resources if isinstance(existing, CatalogAdapter) else []
                merged = {r.id: r for r in [*previous, *[r for r in resources if r.provider == provider]]}
                engine.registry.remove(provider)
                engine.registry.register(CatalogAdapter(provider, merged.values()))
        if args.command == "providers":
            result = engine.registry.describe()
        elif args.command == "diagnostic":
            result = engine.diagnostic(args.concept)
        elif args.command == "diagnose":
            from dataclasses import asdict
            result = asdict(engine.diagnose(**read(args.input)))
        elif args.command in {"recommend", "start", "plan"}:
            request = read(args.input)
            learner = Learner(**request.pop("learner"))
            if args.command == "plan":
                gaps = [Gap(**g) for g in request.pop("gaps")]
                result = engine.study_plan(learner, gaps, **request)
            else:
                gap = Gap(**request.pop("gap"))
                result = getattr(engine, args.command)(learner, gap, **request)
        elif args.command == "activity":
            engine.tracker.record(args.intervention, args.status)
            result = {"status": "recorded", "mastery_updated": False}
        elif args.command == "assess":
            result = engine.evaluator.evaluate(**read(args.input))
        elif args.command == "rubric":
            result = store.intervention(args.intervention)["payload"]["assessment"]
        elif args.command == "mastery":
            result = store.get_mastery(args.learner, args.concept)
        else:
            result = store.history(args.learner, args.concept)
            # History is also a learner-facing endpoint: omit assessment answers.
            for item in result:
                specification = item["payload"]["assessment"]
                item["payload"]["assessment"] = {"id": specification["id"], "prompt": specification["prompt"]}
        print(json.dumps(result, ensure_ascii=True, indent=2))
    except (ValueError, KeyError, OSError, TypeError) as error:
        parser.exit(2, f"{type(error).__name__}: {error}\n")
    finally:
        store.close()


if __name__ == "__main__":
    main()
