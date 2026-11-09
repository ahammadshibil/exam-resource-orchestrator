import fs from "node:fs";
import path from "node:path";
import { ROOT } from "../../config.ts";
import type { LearningReferral, LearningResourceQuery, LearningResourceSearch } from "../core/learning-resources.ts";
import type { SearchProvider } from "../core/search.ts";

interface Directory {
	id: string;
	domains: string[];
	catalog_url: string;
	instruction: string;
	coverage: string;
}
interface Entry {
	title: string;
	url: string;
	provider: string;
	concepts?: string[];
	section?: string;
	language?: string;
	cost?: string;
	license?: string;
	evidence?: string[];
	reference_kind?: string;
	title_basis?: string;
	requirements?: string[];
	min_age?: number;
	countries?: string[];
	blocked_countries?: string[];
	availability?: string;
	link_status?: string;
}

function httpsUrl(value: unknown): value is string {
	if (typeof value !== "string") return false;
	try {
		const url = new URL(value);
		return url.protocol === "https:" && !url.username && !url.password && !url.port;
	} catch { return false; }
}

function terms(value: string): Set<string> {
	return new Set(value.toLowerCase().replace(/^\s*what\s+(is|are)\s+/, "").match(/[\p{L}\p{N}]+/gu)?.filter(word => !["a", "an", "the", "of", "and"].includes(word)) ?? []);
}

function hostProvider(url: string, directories: Directory[]): string | undefined {
	const host = new URL(url).hostname;
	return directories.find(source => source.domains.some(domain => host === domain || host.endsWith("." + domain)))?.id;
}

/** Read-only catalog assets. Not LearnHarness's mutable data/auth directories. */
function loadCatalog(directory: string): { entries: Entry[]; directories: Directory[] } {
	const read = (name: string) => fs.readFileSync(path.join(directory, name), "utf8");
	const directories = JSON.parse(read("sources.json")) as Directory[];
	const entries: Entry[] = [
		...JSON.parse(read("catalog.json")),
		...read("publisher_references.jsonl").trim().split("\n").map(line => JSON.parse(line)),
		...read("hackertube.jsonl").trim().split("\n").map(line => {
			const row = JSON.parse(line);
			return {
				title: row.title, url: row.url, provider: "hackertube",
				concepts: [row.primary_topic, ...(row.tags ?? [])].filter(Boolean),
				language: "und", license: "ODC-By-1.0 for metadata only; original-video rights separate",
				evidence: ["HackerTube https://hackertube.org/data; derived from https://huggingface.co/datasets/open-index/hacker-news"],
			};
		}),
	];
	return { entries: entries.filter(row => typeof row.title === "string" && httpsUrl(row.url)), directories };
}

function referral(row: Entry, input: LearningResourceQuery): LearningReferral {
	const topic = terms(input.query);
	const torque = topic.size === 1 && topic.has("torque")
		&& row.url === "https://openstax.org/books/university-physics-volume-1/pages/10-6-torque";
	const notes = ["Content and current access must be checked on the original provider."];
	if (row.cost !== "free") notes.push(`Cost: ${row.cost ?? "unknown"}.`);
	if (row.requirements?.length) notes.push(`Requires: ${row.requirements.join(", ")}.`);
	if (row.min_age) notes.push(`Minimum age: ${row.min_age}; eligibility not established.`);
	if (row.countries?.length) notes.push(`Listed regions: ${row.countries.join(", ")}.`);
	if (row.blocked_countries?.length) notes.push(`Restricted regions: ${row.blocked_countries.join(", ")}.`);
	if (row.availability === "unavailable" || row.link_status === "restricted" || row.link_status === "unavailable") notes.push(`Source status: ${row.link_status ?? row.availability}; retain link for manual inspection and offer an alternative.`);
	if (row.title_basis === "publisher_url_label") notes.push("Label derived from a publisher URL; actual page heading unverified.");
	if (row.language !== (input.language ?? "en")) notes.push(`Source language: ${row.language ?? "und"}; requested language not confirmed.`);
	return {
		title: row.title, url: row.url, provider: row.provider,
		section: row.section ?? "Exact section and timestamps unverified; locate the topic on the original page",
		kind: row.reference_kind ?? "resource", titleBasis: row.title_basis ?? "source_metadata",
		language: row.language ?? "und", license: row.license ?? "Unknown; link only", evidence: row.evidence ?? [],
		accessNote: notes.join(" "),
		activity: torque
			? "Open section 10.6. Draw the pivot and force line for equal radial and perpendicular pushes at the same distance. Predict which produces more turning effect before calculating. Mark each perpendicular moment arm, then use r F sin(theta) to check your prediction. Explain why force magnitude alone is insufficient. If the source is blocked, ask the tutor for an alternative; opening the link is not completion of the task."
			: `Open the original source and locate ${input.query}. For a whole course/book, select a relevant section first. Predict a result, explain it in your own words, and work one example. Use another source if access is blocked.`,
		followUp: torque
			? "After the learner returns, pose a fresh unaided problem comparing a smaller oblique force with a larger force whose line passes through the pivot. Use different magnitudes, distances and angles from earlier questions. Ask for a prediction, a sketch of the moment arm and a calculation without the source open. Collect the response before showing an answer or rubric. Assess both the numerical result and why the radial force has zero torque; reading completion is not mastery."
			: `Return for a fresh problem on ${input.query} without the source open. Opening a link or reporting completion is not mastery.`,
	};
}

export function createLearningResourceSearch(
	directory = path.join(ROOT, "resources", "learning-catalog"),
	search: () => SearchProvider | null = () => null,
): LearningResourceSearch {
	let catalog: ReturnType<typeof loadCatalog> | undefined;
	return async input => {
		const wanted = terms(input.query);
		const limit = input.limit ?? 2;
		if (!wanted.size || input.query.length > 300 || !Number.isInteger(limit) || limit < 1 || limit > 3) throw new Error("Use a topic of 1–300 characters and a result limit of 1–3");
		catalog ??= loadCatalog(directory);
		const { directories } = catalog;
		const known = new Set(directories.map(source => source.id));
		if (input.providers?.some(id => !known.has(id))) throw new Error("Unknown resource provider; use a listed provider ID");
		const chosen = new Set(input.providers ?? []);
		const warnings: string[] = [];
		const candidates = [...catalog.entries];
		if (input.live) {
			const provider = search();
			if (!provider) warnings.push("Live web search is not configured; using the bundled index and official catalog routes.");
			else {
				const domains = directories.filter(source => chosen.has(source.id)).flatMap(source => source.domains);
				const query = input.query + (domains.length ? ` (${domains.map(domain => `site:${domain}`).join(" OR ")})` : "");
				try {
					for (const hit of await provider.search(query, 5)) {
						if (!httpsUrl(hit.url)) continue;
						const owner = hostProvider(hit.url, directories);
						if (chosen.size && (!owner || !chosen.has(owner))) continue;
						candidates.push({ title: hit.title, url: hit.url, provider: owner ?? "web-references", concepts: [input.query], language: "und", evidence: [`Discovered with configured ${provider.id} search; content and language unverified`] });
					}
				} catch { warnings.push("Live search failed; using bundled references. Provider errors and credentials were not included."); }
			}
		}
		const unique = new Map<string, { row: Entry; score: number }>();
		for (const row of candidates) {
			if (chosen.size && !chosen.has(row.provider)) continue;
			const coverage = terms([row.title, ...(row.concepts ?? []), row.section ?? ""].join(" "));
			if (![...wanted].every(word => coverage.has(word))) continue;
			const direct = [...wanted].every(word => terms(row.title).has(word));
			const accessPenalty = row.availability === "unavailable" || ["restricted", "unavailable"].includes(row.link_status ?? "") || (input.country && row.blocked_countries?.includes(input.country)) ? 100 : 0;
			const score = (direct ? 8 : 4) + (row.language === (input.language ?? "en") ? 2 : 0) + (row.provider !== "hackertube" && known.has(row.provider) ? 1 : 0) + (row.title_basis !== "publisher_url_label" ? 1 : 0) - accessPenalty;
			const current = unique.get(row.url);
			if (!current || score > current.score) unique.set(row.url, { row, score });
		}
		const matches = [...unique.values()].sort((a, b) => b.score - a.score || a.row.url.localeCompare(b.row.url));
		const routes = directories.filter(source => !chosen.size || chosen.has(source.id)).slice(0, 3);
		return {
			query: input.query, references: matches.slice(0, limit).map(({ row }) => referral(row, input)),
			discoveryRoutes: routes.map(source => ({ provider: source.id, url: source.catalog_url, instruction: source.instruction, coverage: source.coverage })),
			totalMatches: matches.length, warnings, contentDownloaded: false, masteryUpdated: false,
		};
	};
}
