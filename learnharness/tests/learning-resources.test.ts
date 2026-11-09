import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import { createHash } from "node:crypto";
import { test } from "node:test";
import { ROOT } from "../config.ts";
import { createLearningResourceSearch } from "../src/server/learning-resources.ts";
import { learningResourceTools } from "../src/agent/tools/learning-resources.ts";
import { createProberTools, createTeacherTools } from "../src/agent/tools.ts";
import { practiceTools } from "../src/agent/tools/practice.ts";
import type { SearchProvider } from "../src/core/search.ts";

test("bundled resources resolve original provider links without keys or network", async () => {
	const search = createLearningResourceSearch();
	for (const [query, provider] of [["photosynthesis", "openstax"], ["linear algebra", "nptel"], ["vectors", "hackertube"]]) {
		const result = await search({ query: query!, providers: [provider!] });
		assert.ok(result.references.length > 0);
		assert.ok(result.references.every(row => row.provider === provider && row.url.startsWith("https://")));
		assert.equal(result.contentDownloaded, false);
		assert.equal(result.masteryUpdated, false);
		assert.ok(result.references.every(row => row.activity && row.followUp && row.accessNote));
	}
});

test("regional-language portal routes stay manual and do not invent lessons", async () => {
	const result = await createLearningResourceSearch()({ query: "cell division", providers: ["diksha"], language: "hi" });
	assert.deepEqual(result.references, []);
	assert.equal(result.discoveryRoutes[0]?.url, "https://diksha.gov.in/explore");
	assert.ok(result.discoveryRoutes[0]?.instruction.includes("language"));
});

test("live discovery is opt-in, domain constrained and ignores snippets", async () => {
	let requests = 0;
	const provider: SearchProvider = { id: "brave", search: async query => {
		requests++;
		assert.ok(query.includes("site:ncert.nic.in"));
		return [{ title: "A unique topic", url: "https://ncert.nic.in/unique", snippet: "SECRET_SNIPPET" },
			{ title: "A unique topic", url: "https://ncert.nic.in.evil.example/unique", snippet: "" }];
	} };
	const search = createLearningResourceSearch(undefined, () => provider);
	await search({ query: "unique topic", providers: ["ncert"] });
	assert.equal(requests, 0);
	const result = await search({ query: "unique topic", providers: ["ncert"], live: true });
	assert.equal(result.references.length, 1);
	assert.ok(!JSON.stringify(result).includes("SECRET_SNIPPET"));
});

test("unavailable live search falls back; invalid providers and limits are refused", async () => {
	const search = createLearningResourceSearch();
	const result = await search({ query: "torque", live: true });
	assert.ok(result.references.length);
	assert.ok(result.warnings[0]?.includes("not configured"));
	await assert.rejects(search({ query: "torque", providers: ["not-real"] }));
	await assert.rejects(search({ query: "torque", limit: 100 }));
});

test("tool registration is injected into all three phases, never a replacement for assessment", () => {
	const search = createLearningResourceSearch();
	const common = { chatId: "fixture", chatStore: { getChat: () => ({ messages: [] }) }, jobStore: {}, spawn: () => {}, deliver: () => {} };
	assert.deepEqual(learningResourceTools(), {});
	assert.ok(createProberTools({ ...common, learningResources: search } as never).learning_resources);
	assert.ok(createTeacherTools({ ...common, learningResources: search } as never).learning_resources);
	const practice = practiceTools({ ...common, learningResources: search } as never);
	assert.ok(practice.learning_resources && practice.problem && practice.conclude);
});

test("packaged catalog snapshots match the retained Python module", () => {
	for (const name of ["catalog.json", "sources.json", "hackertube.jsonl", "publisher_references.jsonl"]) {
		const hash = (file: string) => createHash("sha256").update(fs.readFileSync(file)).digest("hex");
		assert.equal(hash(path.join(ROOT, "resources", "learning-catalog", name)), hash(path.join(ROOT, "..", "exam_resources", "data", name)));
	}
});


test("torque referral targets moment-arm reasoning and requests a fresh unaided check", async () => {
	const search = createLearningResourceSearch();
	const result = await search({ query: "torque", providers: ["openstax"], limit: 1 });
	assert.equal(result.references.length, 1);
	const resource = result.references[0]!;
	assert.equal(resource.url, "https://openstax.org/books/university-physics-volume-1/pages/10-6-torque");
	assert.match(resource.activity, /radial/i);
	assert.match(resource.activity, /perpendicular/i);
	assert.match(resource.activity, /moment arm/i);
	assert.match(resource.followUp, /different.*earlier/i);
	assert.match(resource.followUp, /without.*source/i);
	assert.match(resource.followUp, /before.*answer/i);
	assert.equal(result.contentDownloaded, false);
	assert.equal(result.masteryUpdated, false);
	const unrelated = await search({ query: "photosynthesis", providers: ["openstax"], limit: 1 });
	assert.ok(unrelated.references.length);
	assert.doesNotMatch(unrelated.references[0]!.activity, /radial|moment arm/i);
});
