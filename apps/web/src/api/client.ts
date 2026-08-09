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

export type HealthResponse = z.infer<typeof healthSchema>;
export type VersionResponse = z.infer<typeof versionSchema>;

export class ApiError extends Error {
  public readonly status?: number;

  constructor(message: string, status?: number) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

async function getJson<T>(path: string, schema: z.ZodType<T>): Promise<T> {
  const response = await fetch(`${env.VITE_API_URL}${path}`, {
    headers: { Accept: "application/json" },
  });

  if (!response.ok) {
    throw new ApiError(`API request failed: ${response.statusText}`, response.status);
  }

  return schema.parse(await response.json());
}

export const api = {
  health: () => getJson("/api/v1/health", healthSchema),
  version: () => getJson("/api/v1/version", versionSchema),
};
