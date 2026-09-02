import { loadConfig } from "./loader.js";

export const config = await loadConfig();

export function combine(a: string, b: string): string {
  return a + "::" + b;
}

export const VERSION: string = "1.0.0";
