import { z } from 'zod';
import * as dotenv from 'dotenv';

dotenv.config();

export const ConfigSchema = z.object({
  baseUrl: z.string().default('https://plato.so/api'),
  apiKey: z.string().min(1, 'API key is required'),
});

export type Config = z.infer<typeof ConfigSchema>;

let cachedConfig: Config | null = null;

export function getConfig(): Config {
  if (cachedConfig) {
    return cachedConfig;
  }

  const config = ConfigSchema.parse({
    baseUrl: process.env.PLATO_BASE_URL,
    apiKey: process.env.PLATO_API_KEY,
  });

  cachedConfig = config;
  return config;
} 