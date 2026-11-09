/** Referral port: no downloaded lessons and no writes to learner mastery. */
export interface LearningResourceQuery {
	query: string;
	language?: string;
	country?: string;
	providers?: string[];
	limit?: number;
	live?: boolean;
}

export interface LearningReferral {
	title: string;
	url: string;
	provider: string;
	section: string;
	kind: string;
	titleBasis: string;
	language: string;
	license: string;
	evidence: string[];
	accessNote: string;
	activity: string;
	followUp: string;
}

export interface LearningResourceResult {
	query: string;
	references: LearningReferral[];
	discoveryRoutes: Array<{ provider: string; url: string; instruction: string; coverage: string }>;
	totalMatches: number;
	warnings: string[];
	contentDownloaded: false;
	masteryUpdated: false;
}

export type LearningResourceSearch = (input: LearningResourceQuery) => Promise<LearningResourceResult>;
