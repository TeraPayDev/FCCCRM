export type SessionTokens = {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
};

type StoredSession = {
  tokens: SessionTokens;
  access_expires_at: number;
  last_activity_at: number;
};

const KEY = "cram-auth-session";
export const SESSION_IDLE_TIMEOUT_MS = 30 * 60 * 1000;

function isStoredSession(value: unknown): value is StoredSession {
  if (!value || typeof value !== "object") return false;
  const candidate = value as Partial<StoredSession>;
  return Boolean(candidate.tokens && candidate.access_expires_at && candidate.last_activity_at);
}

export function saveTokens(tokens: SessionTokens): void {
  const stored: StoredSession = {
    tokens,
    access_expires_at: Date.now() + Math.max(1, tokens.expires_in) * 1000,
    last_activity_at: Date.now(),
  };
  sessionStorage.setItem(KEY, JSON.stringify(stored));
}

function readStoredSession(): StoredSession | null {
  const raw = sessionStorage.getItem(KEY);
  if (!raw) return null;
  try {
    const parsed = JSON.parse(raw) as unknown;
    if (isStoredSession(parsed)) return parsed;

    // Backward compatibility for sessions created before timeout tracking was added.
    const legacy = parsed as SessionTokens;
    if (legacy?.access_token && legacy?.refresh_token && typeof legacy.expires_in === "number") {
      const migrated: StoredSession = {
        tokens: legacy,
        access_expires_at: Date.now() + Math.max(1, legacy.expires_in) * 1000,
        last_activity_at: Date.now(),
      };
      sessionStorage.setItem(KEY, JSON.stringify(migrated));
      return migrated;
    }
  } catch {
    // Invalid sessions are cleared below.
  }
  sessionStorage.removeItem(KEY);
  return null;
}

export function loadTokens(): SessionTokens | null {
  const stored = readStoredSession();
  if (!stored) return null;
  if (Date.now() - stored.last_activity_at >= SESSION_IDLE_TIMEOUT_MS) {
    clearTokens();
    return null;
  }
  return stored.tokens;
}

export function touchSession(): void {
  const stored = readStoredSession();
  if (!stored) return;
  stored.last_activity_at = Date.now();
  sessionStorage.setItem(KEY, JSON.stringify(stored));
}

export function isSessionTimedOut(): boolean {
  const stored = readStoredSession();
  return !stored || Date.now() - stored.last_activity_at >= SESSION_IDLE_TIMEOUT_MS;
}

export function clearTokens(): void {
  sessionStorage.removeItem(KEY);
}

export function signalSessionExpired(): void {
  clearTokens();
  if (typeof window !== "undefined") window.dispatchEvent(new Event("cram:session-expired"));
}
