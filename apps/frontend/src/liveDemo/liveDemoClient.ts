import {
  LIVE_DEMO_TOKEN_HEADER,
  type CreateLiveDemoRunRequest,
  type CreateLiveDemoRunResponse,
  type LiveDemoOverview,
  type LiveDemoSopDocumentDetail,
  type LiveDemoSopDocumentListResponse,
  type SseEvent
} from "@agent-py/api-contracts";

import { AUTH_TOKEN_STORAGE_KEY } from "../authClient";
import { createApiClient } from "../api/apiClient";
import { createSseClient } from "../api/sseClient";
import { API_BASE_URL } from "../config";

export interface LiveDemoClient {
  getOverview(): Promise<LiveDemoOverview>;
  createRun(scenarioId: string): Promise<CreateLiveDemoRunResponse>;
  streamRun(runId: string, runToken: string): AsyncIterable<SseEvent>;
  listSopDocuments(): Promise<LiveDemoSopDocumentListResponse>;
  getSopDocument(documentId: string): Promise<LiveDemoSopDocumentDetail>;
}

export interface CreateLiveDemoClientOptions {
  readonly baseUrl?: string;
  readonly fetchImpl?: typeof fetch;
  readonly getAccessToken?: () => string | null;
}

/**
 * Drill client. Creating a run sends the workspace bearer token (when signed in) so the
 * diagnosis is linked to the requester; the event stream only ever uses the run token.
 */
export function createLiveDemoClient(options: CreateLiveDemoClientOptions = {}): LiveDemoClient {
  const getAccessToken = options.getAccessToken ?? (() => window.localStorage.getItem(AUTH_TOKEN_STORAGE_KEY));
  const publicOptions = {
    baseUrl: options.baseUrl ?? API_BASE_URL,
    ...(options.fetchImpl === undefined ? {} : { fetchImpl: options.fetchImpl }),
    getAccessToken: () => null
  };
  const api = createApiClient(publicOptions);
  const authedApi = createApiClient({ ...publicOptions, getAccessToken });
  const sse = createSseClient(publicOptions);

  return {
    getOverview: () => api.request<LiveDemoOverview>("/live-demo"),
    createRun: (scenarioId) => {
      const body: CreateLiveDemoRunRequest = { scenarioId };
      return authedApi.request<CreateLiveDemoRunResponse>("/live-demo/runs", {
        body: JSON.stringify(body),
        method: "POST"
      });
    },
    streamRun: (runId, runToken) =>
      sse.stream(`/live-demo/runs/${encodeURIComponent(runId)}:stream`, {
        headers: { [LIVE_DEMO_TOKEN_HEADER]: runToken },
        method: "POST"
      }),
    listSopDocuments: () => authedApi.request<LiveDemoSopDocumentListResponse>("/live-demo/sop-documents"),
    getSopDocument: (documentId) =>
      authedApi.request<LiveDemoSopDocumentDetail>(`/live-demo/sop-documents/${encodeURIComponent(documentId)}`)
  };
}
