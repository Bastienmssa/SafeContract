export type Severity = "critical" | "medium" | "low";

export interface Issue {
  line: number;
  severity: Severity;
  title: string;
  desc: string;
  swcId: string;
  tool?: string;
  confirmedByGnn?: boolean;
  gnnConfidence?: string;
  gnnDescription?: string;
}

export interface AiVerdict {
  verdict: "vulnerable" | "safe";
  score: number;
  explanation: string;
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
  aiVerdict?: AiVerdict;
}
