import axios from "axios";

export const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8001";

// Allow overriding timeout via env; default to 10 minutes for long git operations
const DEFAULT_TIMEOUT_MS = 600000; // 10 minutes
const ENV_TIMEOUT = Number(import.meta.env.VITE_API_TIMEOUT_MS);
export const apiClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: Number.isFinite(ENV_TIMEOUT) && ENV_TIMEOUT > 0 ? ENV_TIMEOUT : DEFAULT_TIMEOUT_MS,
});

export function buildWebSocketUrl(path: string): string {
  const base = new URL(API_BASE_URL);
  base.protocol = base.protocol === "https:" ? "wss:" : "ws:";
  const normalizedPath = path.startsWith("/") ? path : `/${path}`;
  base.pathname = normalizedPath;
  return base.toString();
}
