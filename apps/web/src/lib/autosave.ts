export interface KeyValueStorage {
  getItem(key: string): string | null;
  setItem(key: string, value: string): void;
  removeItem(key: string): void;
}

/**
 * Returns the next strictly increasing client_seq (>= 1) for a question.
 * Keeps autosaves monotonic across reloads and out-of-order network retries.
 */
export function nextClientSeq(
  currentMap: Record<string, number>,
  questionId: string
): number {
  const prev = currentMap[questionId] ?? 0;
  return Math.max(1, prev + 1);
}

/**
 * Returns a deterministic Idempotency-Key per attempt persisted in sessionStorage
 * so submission retries reuse the exact same key (FR-ATT-04, FR-SEC-05).
 */
export function getOrCreateSubmitKey(
  attemptId: string,
  storage: KeyValueStorage | null = typeof window !== "undefined" ? window.sessionStorage : null
): string {
  const storageKey = `lancast-submit-key:${attemptId}`;
  const existing = storage?.getItem(storageKey);
  if (existing && existing.length >= 8 && existing.length <= 128) {
    return existing;
  }
  const suffix =
    typeof crypto !== "undefined" && typeof crypto.randomUUID === "function"
      ? crypto.randomUUID()
      : `${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 10)}`;
  const key = `submit-${attemptId.slice(0, 18)}-${suffix}`.slice(0, 128);
  storage?.setItem(storageKey, key);
  return key;
}

export function clearSubmitKey(
  attemptId: string,
  storage: KeyValueStorage | null = typeof window !== "undefined" ? window.sessionStorage : null
): void {
  storage?.removeItem(`lancast-submit-key:${attemptId}`);
}
