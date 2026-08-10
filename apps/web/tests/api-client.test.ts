import { afterEach, describe, expect, it, vi } from "vitest";

import { ApiError, api } from "../src/api/client";

describe("CRAM API client", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("parses a valid health response", async () => {
    const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(
        JSON.stringify({
          status: "healthy",
          service: "cram-api",
          version: "0.1.0",
        }),
        {
          status: 200,
          headers: { "Content-Type": "application/json" },
        },
      ),
    );

    await expect(api.health()).resolves.toEqual({
      status: "healthy",
      service: "cram-api",
      version: "0.1.0",
    });

    expect(fetchMock).toHaveBeenCalledTimes(1);
    expect(String(fetchMock.mock.calls[0]?.[0])).toContain("/api/v1/health");
  });

  it("raises ApiError when the API returns a failed response", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response("failure", {
        status: 503,
        statusText: "Service Unavailable",
      }),
    );

    await expect(api.health()).rejects.toMatchObject<ApiError>({
      name: "ApiError",
      status: 503,
    });
  });
});
