import type { ActiveAlert, AiopsDiagnosticStatus } from "./protected-data";

export const LIVE_DEMO_TOKEN_HEADER = "X-Live-Demo-Token";

/** Where drill logs and metrics come from; `simulator` data is synthetic and must be labelled. */
export const LIVE_DEMO_OBSERVABILITY_MODES = ["simulator", "aws-cloudwatch"] as const;
export type LiveDemoObservability = (typeof LIVE_DEMO_OBSERVABILITY_MODES)[number];

export interface LiveDemoScenario {
  readonly id: string;
  readonly title: string;
  readonly service: string;
  readonly alertName: string;
  readonly severity: string;
  readonly symptom: string;
}

export interface LiveDemoQuota {
  readonly visitorLimit: number;
  readonly visitorRemaining: number;
  readonly dailyLimit: number;
  readonly dailyRemaining: number;
  readonly maxConcurrentRuns: number;
  readonly running: number;
}

export interface LiveDemoLatestRun {
  readonly runId: string;
  readonly scenarioId: string;
  readonly scenarioTitle: string;
  readonly startedAt: string;
  readonly completedAt: string;
  readonly durationSeconds: number;
  readonly report: {
    readonly id: string;
    readonly title: string;
    readonly content: string;
    readonly format: "markdown";
  };
}

export interface LiveDemoOverview {
  readonly available: boolean;
  readonly unavailableReason: string | null;
  readonly observability: LiveDemoObservability;
  readonly scenarios: readonly LiveDemoScenario[];
  readonly quota: LiveDemoQuota;
  readonly latestRun: LiveDemoLatestRun | null;
}

export interface CreateLiveDemoRunRequest {
  readonly scenarioId: string;
}

export interface LiveDemoRun {
  readonly id: string;
  readonly scenarioId: string;
  readonly status: AiopsDiagnosticStatus;
  readonly createdAt: string;
  /** Diagnosis id readable via `/aiops/diagnostics/{id}`; null when the run was anonymous. */
  readonly diagnosticId: string | null;
}

export interface CreateLiveDemoRunResponse {
  readonly run: LiveDemoRun;
  readonly runToken: string;
  readonly alert: ActiveAlert;
  readonly alertPublished: boolean;
  readonly observability: LiveDemoObservability;
  readonly quota: LiveDemoQuota;
}

/** Read-only SOP document from the drill environment's knowledge base. */
export interface LiveDemoSopDocument {
  readonly id: string;
  readonly filename: string;
  readonly sizeBytes: number;
  readonly mimeType: string;
  readonly status: string;
  readonly indexStatus: string;
  readonly updatedAt: string;
}

export interface LiveDemoSopDocumentDetail extends LiveDemoSopDocument {
  readonly content: string;
}

export interface LiveDemoSopDocumentListResponse {
  readonly items: readonly LiveDemoSopDocument[];
}
