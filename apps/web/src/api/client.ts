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

const organisationSchema = z.object({
  id: z.string(),
  code: z.string(),
  name: z.string(),
  is_active: z.boolean(),
  created_at: z.string(),
  updated_at: z.string(),
});

const organisationUserSchema = z.object({
  id: z.string(),
  username: z.string(),
  email: z.string(),
  is_active: z.boolean(),
  organisation_id: z.string().nullable(),
  organisation_code: z.string().nullable(),
  organisation_name: z.string().nullable(),
});

export type HealthResponse = z.infer<typeof healthSchema>;
export type VersionResponse = z.infer<typeof versionSchema>;
export type TokenPair = z.infer<typeof tokenPairSchema>;
export type CurrentUser = z.infer<typeof currentUserSchema>;
export type Organisation = z.infer<typeof organisationSchema>;
export type OrganisationUser = z.infer<typeof organisationUserSchema>;

export class ApiError extends Error {
  public readonly status?: number;

  constructor(message: string, status?: number) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

async function errorMessage(response: Response): Promise<string> {
  let message = `API request failed: ${response.statusText}`;
  try {
    const body = (await response.json()) as { detail?: string };
    if (body.detail) message = body.detail;
  } catch {
    // Keep the status text fallback.
  }
  return message;
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
    throw new ApiError(await errorMessage(response), response.status);
  }

  return schema.parse(await response.json());
}

function authHeaders(accessToken: string): HeadersInit {
  return { Authorization: `Bearer ${accessToken}` };
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
      headers: authHeaders(accessToken),
    }),
  logout: async (accessToken: string) => {
    const response = await fetch(`${env.VITE_API_URL}/api/v1/auth/logout`, {
      method: "POST",
      headers: authHeaders(accessToken),
    });
    if (!response.ok && response.status !== 401) {
      throw new ApiError("Logout failed.", response.status);
    }
  },
  organisations: (accessToken: string) =>
    requestJson("/api/v1/organisations", z.array(organisationSchema), {
      headers: authHeaders(accessToken),
    }),
  createOrganisation: (accessToken: string, code: string, name: string) =>
    requestJson("/api/v1/organisations", organisationSchema, {
      method: "POST",
      headers: {
        ...authHeaders(accessToken),
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ code, name }),
    }),
  updateOrganisation: (
    accessToken: string,
    organisationId: string,
    payload: { name?: string; is_active?: boolean },
  ) =>
    requestJson(`/api/v1/organisations/${organisationId}`, organisationSchema, {
      method: "PATCH",
      headers: {
        ...authHeaders(accessToken),
        "Content-Type": "application/json",
      },
      body: JSON.stringify(payload),
    }),
  deleteOrganisation: async (accessToken: string, organisationId: string) => {
    const response = await fetch(`${env.VITE_API_URL}/api/v1/organisations/${organisationId}`, {
      method: "DELETE",
      headers: authHeaders(accessToken),
    });
    if (!response.ok) {
      throw new ApiError(await errorMessage(response), response.status);
    }
  },
  organisationUsers: (accessToken: string) =>
    requestJson("/api/v1/organisations/users", z.array(organisationUserSchema), {
      headers: authHeaders(accessToken),
    }),
  assignUserOrganisation: (accessToken: string, userId: string, organisationId: string | null) =>
    requestJson(`/api/v1/organisations/users/${userId}`, organisationUserSchema, {
      method: "PATCH",
      headers: {
        ...authHeaders(accessToken),
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ organisation_id: organisationId }),
    }),
};
