import { describe, expect, it } from "vitest";

import {
  ACCOUNT_KINDS,
  API_ERROR_CODES,
  LIVE_DEMO_OBSERVABILITY_MODES,
  LIVE_DEMO_TOKEN_HEADER,
  OPENAPI_CONTRACT,
  type CreateLiveDemoRunResponse,
  type LiveDemoOverview
} from "../src";

describe("live incident drill contract", () => {
  it("defines the rate-limit error code", () => {
    expect(API_ERROR_CODES.BUSINESS_RATE_LIMITED).toEqual({
      category: "business",
      httpStatus: 429,
      message: "The request limit has been reached. Please try again later."
    });
  });

  it("documents public live-demo paths without bearer auth", () => {
    const overview = OPENAPI_CONTRACT.paths["/live-demo"].get;
    const create = OPENAPI_CONTRACT.paths["/live-demo/runs"].post;
    const stream = OPENAPI_CONTRACT.paths["/live-demo/runs/{runId}:stream"].post;

    expect(overview.operationId).toBe("getLiveDemoOverview");
    expect("security" in overview).toBe(false);
    expect("security" in create).toBe(false);
    expect(create.responses["429"].description).toBe(API_ERROR_CODES.BUSINESS_RATE_LIMITED.message);
    expect(create.responses["503"]).toBeDefined();
    expect(stream.parameters.map((parameter) => parameter.name)).toContain(LIVE_DEMO_TOKEN_HEADER);
    expect(stream.responses["200"].content["text/event-stream"]).toBeDefined();
    expect(stream.responses["403"]).toBeDefined();
  });

  it("types overview and run creation payloads", () => {
    const overview: LiveDemoOverview = {
      available: true,
      unavailableReason: null,
      observability: "simulator",
      scenarios: [{
        id: "java-ecom-order-db-pool-exhausted",
        title: "订单库连接池耗尽",
        service: "order-service",
        alertName: "OrderDatabasePoolExhausted",
        severity: "critical",
        symptom: "订单创建请求排队。"
      }],
      quota: {
        visitorLimit: 3,
        visitorRemaining: 3,
        dailyLimit: 50,
        dailyRemaining: 50,
        maxConcurrentRuns: 2,
        running: 0
      },
      latestRun: null
    };
    const created: CreateLiveDemoRunResponse = {
      run: { id: "live_run_1", scenarioId: "java-ecom-order-db-pool-exhausted", status: "accepted", createdAt: "2026-11-07T00:00:00+00:00", diagnosticId: null },
      runToken: "token",
      alert: {
        id: "live-drill:live_run_1",
        source: "local-alertmanager",
        alertName: "OrderDatabasePoolExhausted",
        service: "order-service",
        severity: "critical",
        status: "firing",
        startsAt: "2026-11-07T00:00:00Z",
        summary: "订单创建请求排队。",
        labels: {},
        annotations: {},
        context: {}
      },
      alertPublished: true,
      observability: "simulator",
      quota: overview.quota
    };

    expect(overview.scenarios[0]?.id).toBe(created.run.scenarioId);
    expect(LIVE_DEMO_OBSERVABILITY_MODES).toEqual(["simulator", "aws-cloudwatch"]);
    const schemas = OPENAPI_CONTRACT.components.schemas;
    expect(schemas.LiveDemoOverviewResponse.required).toContain("observability");
    expect(schemas.CreateLiveDemoRunResponse.required).toContain("observability");
  });

  it("documents guest entry and the read-only drill SOP library", () => {
    const guest = OPENAPI_CONTRACT.paths["/auth/guest"].post;
    const sopList = OPENAPI_CONTRACT.paths["/live-demo/sop-documents"].get;
    const sopDetail = OPENAPI_CONTRACT.paths["/live-demo/sop-documents/{documentId}"].get;
    const schemas = OPENAPI_CONTRACT.components.schemas;

    expect(guest.operationId).toBe("enterAsGuest");
    expect("security" in guest).toBe(false);
    expect(guest.responses["201"]).toBeDefined();
    expect(guest.responses["429"].description).toBe(API_ERROR_CODES.BUSINESS_RATE_LIMITED.message);
    expect(sopList.security).toEqual([{ bearerAuth: [] }]);
    expect(sopDetail.security).toEqual([{ bearerAuth: [] }]);
    expect(schemas.AuthUser.required).toContain("accountKind");
    expect(schemas.AuthUser.properties.accountKind.enum).toEqual([...ACCOUNT_KINDS]);
    expect(schemas.AiopsDiagnosticResponse.properties.origin.enum).toEqual(["workspace", "live-drill"]);
    expect(schemas.LiveDemoSopDocumentDetailResponse.required).toContain("content");
    expect(schemas.LiveDemoSopDocument.required).not.toContain("ownerUserId");
  });
});
