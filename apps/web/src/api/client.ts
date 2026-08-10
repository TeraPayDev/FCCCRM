import { z } from "zod";
import { env } from "../config/env";

const healthSchema = z.object({
  status: z.string(),
  service: z.string(),
  version: z.string(),
});

const versionSchema = z.object({
  service: z.string(),
  version: z.string(),
  environment: z.string(),
});

const tokenPairSchema = z.object({
  access_token: z.string(),
  refresh_token: z.string(),
  token_type: z.string(),
  expires_in: z.number(),
});

const currentUserSchema = z.object({
  id: z.string(),
  username: z.string(),
  email: z.string(),
  organisation_id: z.string().nullable(),
  roles: z.array(z.string()),
  permissions: z.array(z.string()),
});

export type HealthResponse = z.infer<typeof healthSchema>;
export type VersionResponse = z.infer<typeof versionSchema>;
export type TokenPair = z.infer<typeof tokenPairSchema>;
export type CurrentUser = z.infer<typeof currentUserSchema>;

export class ApiError extends Error {
  public readonly status?: number;

  constructor(message: string, status?: number) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

async function requestJson<T>(path: string, schema: z.ZodType<T>, init?: RequestInit): Promise<T> {
  const response = await fetch(`${env.VITE_API_URL}${path}`, {
    ...init,
    headers: {
      Accept: "application/json",
      ...(init?.headers ?? {}),
    },
  });

  if (!response.ok) {
    let message = `API request failed: ${response.statusText}`;
    try {
      const body = (await response.json()) as { detail?: string };
      if (body.detail) message = body.detail;
    } catch {
      // Keep the status text fallback.
    }
    throw new ApiError(message, response.status);
  }

  return schema.parse(await response.json());
}

export const api = {
  health: () => requestJson("/api/v1/health", healthSchema),
  version: () => requestJson("/api/v1/version", versionSchema),
  login: (username: string, password: string) =>
    requestJson("/api/v1/auth/login", tokenPairSchema, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ username, password }),
    }),
  refresh: (refreshToken: string) =>
    requestJson("/api/v1/auth/refresh", tokenPairSchema, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ refresh_token: refreshToken }),
    }),
  me: (accessToken: string) =>
    requestJson("/api/v1/auth/me", currentUserSchema, {
      headers: { Authorization: `Bearer ${accessToken}` },
    }),
  logout: async (accessToken: string) => {
    const response = await fetch(`${env.VITE_API_URL}/api/v1/auth/logout`, {
      method: "POST",
      headers: { Authorization: `Bearer ${accessToken}` },
    });
    if (!response.ok && response.status !== 401) {
      throw new ApiError("Logout failed.", response.status);
    }
  },
};
