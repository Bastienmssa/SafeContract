export type Severity = "critical" | "medium" | "low";

export interface Issue {
  line: number;
  severity: Severity;
  title: string;
  desc: string;
  swcId: string;
}

export interface Contract {
  id: string;
  name: string;
  score: number;
  issues: Issue[];
  lastAnalyzed: string;
  timeline: { date: string; score: number }[];
  code: string;
}
