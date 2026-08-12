import { z } from "zod";
import { env } from "../config/env";
import { loadTokens, saveTokens, signalSessionExpired } from "../auth/session";

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

let refreshPromise: Promise<TokenPair | null> | null = null;

async function refreshSession(): Promise<TokenPair | null> {
  if (refreshPromise) return refreshPromise;

  refreshPromise = (async () => {
    const session = loadTokens();
    if (!session?.refresh_token) {
      signalSessionExpired();
      return null;
    }

    const response = await fetch(`${env.VITE_API_URL}/api/v1/auth/refresh`, {
      method: "POST",
      headers: { "Content-Type": "application/json", Accept: "application/json" },
      body: JSON.stringify({ refresh_token: session.refresh_token }),
    });

    if (!response.ok) {
      signalSessionExpired();
      return null;
    }

    const tokens = tokenPairSchema.parse(await response.json());
    saveTokens(tokens);
    return tokens;
  })().finally(() => {
    refreshPromise = null;
  });

  return refreshPromise;
}

async function fetchWithSessionRetry(path: string, init?: RequestInit): Promise<Response> {
  const url = `${env.VITE_API_URL}${path}`;
  const headers = new Headers(init?.headers);
  if (!headers.has("Accept")) headers.set("Accept", "application/json");

  let response = await fetch(url, { ...init, headers });
  if (response.status !== 401 || !headers.has("Authorization")) return response;

  const refreshed = await refreshSession();
  if (!refreshed) {
    throw new ApiError("Your session expired. Please sign in again.", 401);
  }

  headers.set("Authorization", `Bearer ${refreshed.access_token}`);
  response = await fetch(url, { ...init, headers });
  return response;
}

async function requestJson<T>(path: string, schema: z.ZodType<T>, init?: RequestInit): Promise<T> {
  const response = await fetchWithSessionRetry(path, init);

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

const auditEventSchema = z.object({
  id: z.string(),
  actor_user_id: z.string().nullable(),
  organisation_id: z.string().nullable(),
  action: z.string(),
  resource_type: z.string(),
  resource_id: z.string().nullable(),
  details: z.record(z.string(), z.unknown()),
  occurred_at: z.string(),
});

const spatialLayerSchema = z.object({
  id: z.string(),
  dataset_version_id: z.string().nullable(),
  name: z.string(),
  workspace: z.string().nullable(),
  store_name: z.string().nullable(),
  layer_name: z.string().nullable(),
  geometry_type: z.string().nullable(),
  srid: z.number().nullable(),
  description: z.string().nullable(),
  created_at: z.string(),
  updated_at: z.string(),
});

const geographicAreaSchema = z.object({
  id: z.string(),
  parent_id: z.string().nullable(),
  code: z.string(),
  name: z.string(),
  area_type: z.string(),
  metadata: z.record(z.string(), z.unknown()),
  geometry: z.record(z.string(), z.unknown()).nullable(),
  centroid: z.record(z.string(), z.unknown()).nullable(),
});

export type AuditEvent = z.infer<typeof auditEventSchema>;
export type SpatialLayer = z.infer<typeof spatialLayerSchema>;
export type GeographicArea = z.infer<typeof geographicAreaSchema>;

export const milestone78Api = {
  auditEvents: (accessToken: string, query = "") =>
    requestJson(`/api/v1/audit${query ? `?${query}` : ""}`, z.array(auditEventSchema), {
      headers: authHeaders(accessToken),
    }),
  spatialLayers: (accessToken: string) =>
    requestJson("/api/v1/gis/layers", z.array(spatialLayerSchema), {
      headers: authHeaders(accessToken),
    }),
  geographicAreas: (accessToken: string, bbox?: string) =>
    requestJson(
      `/api/v1/gis/areas${bbox ? `?bbox=${encodeURIComponent(bbox)}` : ""}`,
      z.array(geographicAreaSchema),
      { headers: authHeaders(accessToken) },
    ),
};

const datasetSchema = z.object({
  id: z.string(),
  code: z.string(),
  name: z.string(),
  description: z.string().nullable(),
  owner_organisation_id: z.string(),
  category: z.string().nullable(),
  sensitivity: z.string(),
  expected_format: z.string(),
  update_frequency: z.string().nullable(),
  status: z.string(),
  created_at: z.string(),
  updated_at: z.string(),
});

const datasetPageSchema = z.object({
  items: z.array(datasetSchema),
  total: z.number(),
  offset: z.number(),
  limit: z.number(),
});

const datasetSourceSchema = z.object({
  id: z.string(),
  dataset_id: z.string(),
  provider_organisation_id: z.string().nullable(),
  name: z.string(),
  source_type: z.string(),
  source_reference: z.string().nullable(),
  connection_secret_ref: z.string().nullable(),
  update_method: z.string().nullable(),
  created_at: z.string(),
  updated_at: z.string(),
});

const datasetFieldSchema = z.object({
  id: z.string(),
  dataset_id: z.string(),
  name: z.string(),
  data_type: z.string(),
  ordinal: z.number(),
  is_required: z.boolean(),
  description: z.string().nullable(),
  validation_rules: z.record(z.string(), z.unknown()),
  created_at: z.string(),
  updated_at: z.string(),
});

const datasetVersionSchema = z.object({
  id: z.string(),
  dataset_id: z.string(),
  source_id: z.string().nullable(),
  version_number: z.number(),
  status: z.string(),
  checksum_sha256: z.string().nullable(),
  row_count: z.number().nullable(),
  published_at: z.string().nullable(),
  created_at: z.string(),
  updated_at: z.string(),
});

const datasetUploadSchema = z.object({
  id: z.string(),
  dataset_version_id: z.string(),
  uploaded_by_user_id: z.string().nullable(),
  object_key: z.string(),
  original_filename: z.string(),
  mime_type: z.string().nullable(),
  size_bytes: z.number(),
  checksum_sha256: z.string().nullable(),
  created_at: z.string(),
  updated_at: z.string(),
});

const validationErrorSchema = z.object({
  id: z.string(),
  validation_run_id: z.string(),
  row_number: z.number().nullable(),
  field_name: z.string().nullable(),
  rule_code: z.string(),
  severity: z.string(),
  message: z.string(),
  value_excerpt: z.string().nullable(),
  created_at: z.string(),
});

const validationRunSchema = z.object({
  id: z.string(),
  dataset_version_id: z.string(),
  status: z.string(),
  execution_mode: z.string(),
  started_at: z.string().nullable(),
  completed_at: z.string().nullable(),
  total_rows: z.number(),
  error_count: z.number(),
  warning_count: z.number(),
  created_at: z.string(),
  updated_at: z.string(),
  errors: z.array(validationErrorSchema),
});

const approvalSchema = z.object({
  id: z.string(),
  dataset_version_id: z.string(),
  submitted_by_user_id: z.string().nullable(),
  reviewed_by_user_id: z.string().nullable(),
  status: z.string(),
  comments: z.string().nullable(),
  submitted_at: z.string(),
  reviewed_at: z.string().nullable(),
  created_at: z.string(),
  updated_at: z.string(),
});

export type Dataset = z.infer<typeof datasetSchema>;
export type DatasetPage = z.infer<typeof datasetPageSchema>;
export type DatasetSource = z.infer<typeof datasetSourceSchema>;
export type DatasetField = z.infer<typeof datasetFieldSchema>;
export type DatasetVersion = z.infer<typeof datasetVersionSchema>;
export type DatasetUpload = z.infer<typeof datasetUploadSchema>;
export type ValidationRun = z.infer<typeof validationRunSchema>;
export type Approval = z.infer<typeof approvalSchema>;

export const dataPlatformApi = {
  datasets: (accessToken: string, query = "") =>
    requestJson(`/api/v1/datasets${query ? `?${query}` : ""}`, datasetPageSchema, {
      headers: authHeaders(accessToken),
    }),
  dataset: (accessToken: string, datasetId: string) =>
    requestJson(`/api/v1/datasets/${datasetId}`, datasetSchema, {
      headers: authHeaders(accessToken),
    }),
  createDataset: (
    accessToken: string,
    payload: {
      code: string;
      name: string;
      description?: string;
      owner_organisation_id: string;
      category?: string;
      sensitivity: string;
      expected_format: string;
      update_frequency?: string;
    },
  ) =>
    requestJson("/api/v1/datasets", datasetSchema, {
      method: "POST",
      headers: { ...authHeaders(accessToken), "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    }),
  sources: (accessToken: string, datasetId: string) =>
    requestJson(`/api/v1/datasets/${datasetId}/sources`, z.array(datasetSourceSchema), {
      headers: authHeaders(accessToken),
    }),
  createSource: (
    accessToken: string,
    datasetId: string,
    payload: {
      provider_organisation_id?: string | null;
      name: string;
      source_type: string;
      source_reference?: string;
      connection_secret_ref?: string;
      update_method?: string;
    },
  ) =>
    requestJson(`/api/v1/datasets/${datasetId}/sources`, datasetSourceSchema, {
      method: "POST",
      headers: { ...authHeaders(accessToken), "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    }),
  fields: (accessToken: string, datasetId: string) =>
    requestJson(`/api/v1/datasets/${datasetId}/fields`, z.array(datasetFieldSchema), {
      headers: authHeaders(accessToken),
    }),
  createField: (
    accessToken: string,
    datasetId: string,
    payload: {
      name: string;
      data_type: string;
      ordinal: number;
      is_required: boolean;
      validation_rules: Record<string, unknown>;
    },
  ) =>
    requestJson(`/api/v1/datasets/${datasetId}/fields`, datasetFieldSchema, {
      method: "POST",
      headers: { ...authHeaders(accessToken), "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    }),
  versions: (accessToken: string, datasetId: string) =>
    requestJson(`/api/v1/datasets/${datasetId}/versions`, z.array(datasetVersionSchema), {
      headers: authHeaders(accessToken),
    }),
  uploadCsv: async (accessToken: string, datasetId: string, file: File, sourceId?: string) => {
    const params = new URLSearchParams({ filename: file.name });
    if (sourceId) params.set("source_id", sourceId);
    const response = await fetchWithSessionRetry(
      `/api/v1/datasets/${datasetId}/uploads?${params.toString()}`,
      {
        method: "POST",
        headers: { ...authHeaders(accessToken), "Content-Type": file.type || "text/csv" },
        body: file,
      },
    );
    if (!response.ok) throw new ApiError(await errorMessage(response), response.status);
    return datasetUploadSchema.parse(await response.json());
  },
  validateVersion: (accessToken: string, versionId: string, background = false) =>
    requestJson(
      `/api/v1/datasets/versions/${versionId}/validate?background=${String(background)}`,
      validationRunSchema,
      { method: "POST", headers: authHeaders(accessToken) },
    ),
  validations: (accessToken: string, versionId: string) =>
    requestJson(
      `/api/v1/datasets/versions/${versionId}/validations`,
      z.array(validationRunSchema),
      { headers: authHeaders(accessToken) },
    ),
  submitVersion: (accessToken: string, versionId: string) =>
    requestJson(`/api/v1/datasets/versions/${versionId}/submit`, approvalSchema, {
      method: "POST",
      headers: authHeaders(accessToken),
    }),
  approvals: (accessToken: string) =>
    requestJson("/api/v1/datasets/approvals", z.array(approvalSchema), {
      headers: authHeaders(accessToken),
    }),
  approve: (accessToken: string, approvalId: string, comments = "") =>
    requestJson(`/api/v1/datasets/approvals/${approvalId}/approve`, approvalSchema, {
      method: "POST",
      headers: { ...authHeaders(accessToken), "Content-Type": "application/json" },
      body: JSON.stringify({ comments }),
    }),
  reject: (accessToken: string, approvalId: string, comments = "") =>
    requestJson(`/api/v1/datasets/approvals/${approvalId}/reject`, approvalSchema, {
      method: "POST",
      headers: { ...authHeaders(accessToken), "Content-Type": "application/json" },
      body: JSON.stringify({ comments }),
    }),
  publish: (accessToken: string, versionId: string) =>
    requestJson(`/api/v1/datasets/versions/${versionId}/publish`, datasetVersionSchema, {
      method: "POST",
      headers: authHeaders(accessToken),
    }),
};

const unknownArraySchema = z.array(z.record(z.string(), z.unknown()));
const unknownObjectSchema = z.record(z.string(), z.unknown());

export const roadmapApi = {
  list: (accessToken: string, path: string) =>
    requestJson(path, unknownArraySchema, { headers: authHeaders(accessToken) }),
  object: (accessToken: string, path: string) =>
    requestJson(path, unknownObjectSchema, { headers: authHeaders(accessToken) }),
  post: (accessToken: string, path: string, payload?: Record<string, unknown>) =>
    requestJson(path, unknownObjectSchema, {
      method: "POST",
      headers: { ...authHeaders(accessToken), "Content-Type": "application/json" },
      body: payload ? JSON.stringify(payload) : undefined,
    }),
};

export const citizenApi = {
  submit: (payload: Record<string, unknown>) =>
    requestJson("/api/v1/citizen-reports", unknownObjectSchema, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    }),
  uploadPhoto: async (reportId: string, file: File) => {
    const response = await fetch(
      `${env.VITE_API_URL}/api/v1/citizen-reports/${reportId}/attachments`,
      {
        method: "POST",
        headers: { "Content-Type": file.type, "X-Filename": file.name },
        body: file,
      },
    );
    if (!response.ok) throw new ApiError(await errorMessage(response), response.status);
    return unknownObjectSchema.parse(await response.json());
  },
};
