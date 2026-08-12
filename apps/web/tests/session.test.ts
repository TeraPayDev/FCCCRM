import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import {
  SESSION_IDLE_TIMEOUT_MS,
  isSessionTimedOut,
  loadTokens,
  saveTokens,
  touchSession,
} from "../src/auth/session";

class MemoryStorage implements Storage {
  private values = new Map<string, string>();

  get length(): number {
    return this.values.size;
  }

  clear(): void {
    this.values.clear();
  }

  getItem(key: string): string | null {
    return this.values.get(key) ?? null;
  }

  key(index: number): string | null {
    return [...this.values.keys()][index] ?? null;
  }

  removeItem(key: string): void {
    this.values.delete(key);
  }

  setItem(key: string, value: string): void {
    this.values.set(key, value);
  }
}

describe("CRAM session state", () => {
  beforeEach(() => {
    vi.stubGlobal("sessionStorage", new MemoryStorage());
  });

  afterEach(() => {
    vi.restoreAllMocks();
    vi.unstubAllGlobals();
  });

  it("keeps an active session and refreshes its activity timestamp", () => {
    let now = 1_000_000;
    vi.spyOn(Date, "now").mockImplementation(() => now);

    saveTokens({
      access_token: "access",
      refresh_token: "refresh",
      token_type: "bearer",
      expires_in: 900,
    });

    now += 5 * 60 * 1000;
    touchSession();
    now += 20 * 60 * 1000;

    expect(isSessionTimedOut()).toBe(false);
    expect(loadTokens()?.access_token).toBe("access");
  });

  it("clears a session after the idle timeout", () => {
    let now = 2_000_000;
    vi.spyOn(Date, "now").mockImplementation(() => now);

    saveTokens({
      access_token: "access",
      refresh_token: "refresh",
      token_type: "bearer",
      expires_in: 900,
    });

    now += SESSION_IDLE_TIMEOUT_MS + 1;

    expect(isSessionTimedOut()).toBe(true);
    expect(loadTokens()).toBeNull();
    expect(sessionStorage.length).toBe(0);
  });
});
