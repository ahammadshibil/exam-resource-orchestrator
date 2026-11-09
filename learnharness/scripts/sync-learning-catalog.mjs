/** Copy only the public metadata snapshots and attribution, never learner state. */
import fs from "node:fs";
import path from "node:path";

const app = path.resolve(import.meta.dirname, "..");
const repository = path.resolve(app, "..");
const destination = path.join(app, "resources", "learning-catalog");
fs.mkdirSync(destination, { recursive: true });
for (const name of ["catalog.json", "sources.json", "hackertube.jsonl", "publisher_references.jsonl"]) {
	fs.copyFileSync(path.join(repository, "exam_resources", "data", name), path.join(destination, name));
}
fs.copyFileSync(path.join(repository, "THIRD_PARTY_NOTICES.md"), path.join(destination, "THIRD_PARTY_NOTICES.md"));
console.log("Synced four public metadata files and attribution; no learner databases or credentials copied.");
