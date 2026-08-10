import type { TokenPair } from "../api/client";

const KEY = "cram-auth-session";

export function saveTokens(tokens: TokenPair): void {
  sessionStorage.setItem(KEY, JSON.stringify(tokens));
}

export function loadTokens(): TokenPair | null {
  const raw = sessionStorage.getItem(KEY);
  if (!raw) return null;
  try {
    return JSON.parse(raw) as TokenPair;
  } catch {
    sessionStorage.removeItem(KEY);
    return null;
  }
}

export function clearTokens(): void {
  sessionStorage.removeItem(KEY);
}
