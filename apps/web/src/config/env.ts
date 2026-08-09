import { z } from "zod";

const envSchema = z.object({
  VITE_API_URL: z.string().url().default("http://10.1.11.7:8000"),
});

export const env = envSchema.parse({
  VITE_API_URL: import.meta.env.VITE_API_URL,
});
