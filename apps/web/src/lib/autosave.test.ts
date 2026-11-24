import { describe, expect, it } from "vitest";
import { extractErrorMessage } from "./api";
import {
  clearSubmitKey,
  getOrCreateSubmitKey,
  KeyValueStorage,
  nextClientSeq,
} from "./autosave";

function memoryStorage(): KeyValueStorage {
  const store = new Map<string, string>();
  return {
    getItem: (k) => store.get(k) ?? null,
    setItem: (k, v) => {
      store.set(k, v);
    },
    removeItem: (k) => {
      store.delete(k);
    },
  };
}

describe("autosave & idempotency helpers", () => {
  it("generates monotonic client_seq values per question", () => {
    const seqs: Record<string, number> = {};
    expect(nextClientSeq(seqs, "q1")).toBe(1);
    seqs.q1 = 1;
    expect(nextClientSeq(seqs, "q1")).toBe(2);
    expect(nextClientSeq(seqs, "q2")).toBe(1);
    seqs.q1 = 14;
    expect(nextClientSeq(seqs, "q1")).toBe(15);
  });

  it("persists and reuses a deterministic Idempotency-Key per attempt", () => {
    const storage = memoryStorage();
    const k1 = getOrCreateSubmitKey("attempt-123", storage);
    const k2 = getOrCreateSubmitKey("attempt-123", storage);
    const other = getOrCreateSubmitKey("attempt-999", storage);

    expect(k1).toBe(k2);
    expect(k1.length).toBeGreaterThanOrEqual(8);
    expect(k1.length).toBeLessThanOrEqual(128);
    expect(other).not.toBe(k1);

    clearSubmitKey("attempt-123", storage);
    const k3 = getOrCreateSubmitKey("attempt-123", storage);
    expect(k3).not.toBe(k1);
  });
});

describe("extractErrorMessage", () => {
  it("parses LANCAST structured error detail", () => {
    expect(
      extractErrorMessage({
        detail: { code: "VERSION_FROZEN", message: "Published assessments are frozen" },
      })
    ).toEqual({
      code: "VERSION_FROZEN",
      message: "Published assessments are frozen",
    });
  });

  it("parses FastAPI validation error arrays", () => {
    const parsed = extractErrorMessage({
      detail: [{ loc: ["body", "password"], msg: "String should have at least 10 characters" }],
    });
    expect(parsed.code).toBe("VALIDATION_ERROR");
    expect(parsed.message).toBe("password: String should have at least 10 characters");
  });

  it("falls back cleanly on unknown payloads", () => {
    expect(extractErrorMessage(null, "Fallback")).toEqual({
      code: "API_ERROR",
      message: "Fallback",
    });
  });
});
