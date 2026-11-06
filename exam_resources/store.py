"""SQLite persistence. Completion is never a mastery event."""
import json
import sqlite3
from dataclasses import asdict
from .models import Resource, now


class ResourceMetadataStore:
    def __init__(self, path=":memory:"):
        self.db = sqlite3.connect(path)
        self.db.row_factory = sqlite3.Row
        self.db.executescript('''
            CREATE TABLE IF NOT EXISTS resources(id TEXT PRIMARY KEY, payload TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS interventions(
                id TEXT PRIMARY KEY, learner TEXT NOT NULL, concept TEXT NOT NULL,
                resource TEXT NOT NULL, payload TEXT NOT NULL, created_at TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS events(
                id INTEGER PRIMARY KEY, intervention TEXT NOT NULL, kind TEXT NOT NULL,
                payload TEXT NOT NULL, created_at TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS mastery(
                learner TEXT NOT NULL, concept TEXT NOT NULL, payload TEXT NOT NULL,
                PRIMARY KEY(learner, concept));
        ''')

    def close(self):
        self.db.close()

    def put(self, resource):
        with self.db:
            self.db.execute("INSERT OR REPLACE INTO resources VALUES (?,?)",
                            (resource.id, json.dumps(asdict(resource))))

    def resources(self):
        return [Resource(**json.loads(r[0])) for r in self.db.execute("SELECT payload FROM resources ORDER BY id")]

    def start(self, identifier, learner, gap, prescription, assessment):
        payload = {"gap": asdict(gap), "prescription": prescription.to_dict(), "assessment": asdict(assessment)}
        with self.db:
            self.db.execute("INSERT INTO interventions VALUES (?,?,?,?,?,?)",
                            (identifier, learner.id, gap.concept, prescription.resource.id, json.dumps(payload), now()))

    def intervention(self, identifier):
        row = self.db.execute("SELECT * FROM interventions WHERE id=?", (identifier,)).fetchone()
        if row is None:
            raise KeyError(f"Unknown intervention: {identifier}")
        return {**dict(row), "payload": json.loads(row["payload"])}

    def event(self, identifier, kind, payload):
        self.intervention(identifier)
        with self.db:
            self.db.execute("INSERT INTO events(intervention,kind,payload,created_at) VALUES (?,?,?,?)",
                            (identifier, kind, json.dumps(payload), now()))

    def events(self, identifier):
        return [{**dict(r), "payload": json.loads(r["payload"])} for r in self.db.execute(
            "SELECT * FROM events WHERE intervention=? ORDER BY id", (identifier,))]

    def history(self, learner, concept=None):
        rows = self.db.execute("SELECT id FROM interventions WHERE learner=? ORDER BY created_at", (learner,))
        result = [self.intervention(r[0]) for r in rows]
        return [r for r in result if concept is None or r["concept"] == concept]

    def get_mastery(self, learner, concept):
        row = self.db.execute("SELECT payload FROM mastery WHERE learner=? AND concept=?", (learner, concept)).fetchone()
        return json.loads(row[0]) if row else None

    def set_mastery(self, learner, concept, value):
        with self.db:
            self.db.execute("INSERT OR REPLACE INTO mastery VALUES (?,?,?)", (learner, concept, json.dumps(value)))
