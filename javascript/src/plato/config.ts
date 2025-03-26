import { z } from 'zod';

export const ConfigSchema = z.object({
  baseUrl: z.string().default('https://plato.so/api'),
  apiKey: z.string().min(1, 'API key is required'),
});

export type Config = z.infer<typeof ConfigSchema>;

/**
 * Creates a configuration object with the provided API key and base URL.
 * This function is browser-compatible and does not rely on Node.js specific APIs.
 * 
 * @param apiKey - Required API key for authentication with Plato services
 * @param baseUrl - Optional base URL for the Plato API (defaults to https://plato.so/api)
 * @returns A validated configuration object
 */
export function getConfig(apiKey: string, baseUrl?: string): Config {
  if (!apiKey) {
    throw new Error('API key is required');
  }
  
  return {
    baseUrl: baseUrl || 'https://plato.so/api',
    apiKey,
  };
} 