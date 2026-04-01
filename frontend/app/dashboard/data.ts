export type Severity = "critical" | "medium" | "low";

export interface Issue {
  line: number;
  severity: Severity;
  title: string;
  desc: string;
  swcId: string;
  tool?: string;
}

export interface Contract {
  id: string;
  name: string;
  score: number;
  issues: Issue[];
  lastAnalyzed: string;
  timeline: { date: string; score: number }[];
  code: string;
  toolsUsed?: string[];
  toolsErrors?: Record<string, string>;
  toolsVersions?: Record<string, string>;
}
