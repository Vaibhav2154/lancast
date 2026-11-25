import { ChangeEvent, useCallback, useEffect, useRef, useState } from "react";
import { Link, useLocation, useParams } from "react-router-dom";
import {
  AlertTriangle,
  ArrowLeft,
  ArrowRight,
  CheckCircle2,
  Clock,
  Moon,
  Play,
  Send,
  Sun,
  Upload,
} from "lucide-react";
import { CodeEditor } from "../components/CodeEditor";
import { StatusBadge } from "../components/StatusBadge";
import { useTheme } from "../hooks/useTheme";
import {
  ApiError,
  AttemptView,
  CandidateQuestion,
  CodeRunResponse,
  getAttempt,
  getAttemptSubmission,
  runAttemptCode,
  saveAttemptResponse,
  SubmissionResult,
  submitAttempt,
  uploadAttemptFile,
} from "../lib/api";
import { clearSubmitKey, getOrCreateSubmitKey, nextClientSeq } from "../lib/autosave";

type SaveState = "idle" | "saving" | "saved" | "error";

const LANGUAGE_LABELS: Record<string, string> = {
  python3: "Python 3",
  c: "C",
  cpp: "C++",
  java: "Java",
  javascript: "JavaScript",
};

function formatClock(totalSeconds: number): string {
  const s = Math.max(0, totalSeconds);
  const hrs = Math.floor(s / 3600);
  const mins = Math.floor((s % 3600) / 60);
  const secs = s % 60;
  const pad = (n: number) => String(n).padStart(2, "0");
  return hrs > 0 ? `${hrs}:${pad(mins)}:${pad(secs)}` : `${pad(mins)}:${pad(secs)}`;
}

export function ExamRunnerPage() {
  const { attemptId } = useParams<{ attemptId: string }>();
  const location = useLocation();
  const { theme, toggleTheme } = useTheme();

  const navState = location.state as { initialAttempt?: AttemptView; title?: string } | null;

  const [attempt, setAttempt] = useState<AttemptView | null>(navState?.initialAttempt ?? null);
  const title = navState?.title ?? attempt?.assessment_title ?? "LANCAST Assessment";
  const [currentIdx, setCurrentIdx] = useState(0);
  const [drafts, setDrafts] = useState<Record<string, Record<string, unknown>>>({});
  const [remainingSeconds, setRemainingSeconds] = useState<number>(
    navState?.initialAttempt?.remaining_seconds ?? 0
  );

  const [saveState, setSaveState] = useState<SaveState>("idle");
  const [lastSeq, setLastSeq] = useState<number | null>(null);
  const [saveError, setSaveError] = useState<string | null>(null);

  const [loading, setLoading] = useState(!navState?.initialAttempt);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [uploading, setUploading] = useState(false);

  const [confirmSubmit, setConfirmSubmit] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [autoSubmitting, setAutoSubmitting] = useState(false);
  const [submission, setSubmission] = useState<SubmissionResult | null>(null);

  const [useCustomStdin, setUseCustomStdin] = useState<Record<string, boolean>>({});
  const [customStdin, setCustomStdin] = useState<Record<string, string>>({});
  const [runningCode, setRunningCode] = useState(false);
  const [runResults, setRunResults] = useState<Record<string, CodeRunResponse>>({});
  const [runErrors, setRunErrors] = useState<Record<string, string | null>>({});

  const seqRef = useRef<Record<string, number>>({});
  const debounceRef = useRef<Record<string, number>>({});
  const draftsRef = useRef<Record<string, Record<string, unknown>>>({});
  const pendingDirtyRef = useRef<Set<string>>(new Set());
  const submittingRef = useRef(false);
  const autoSubmittedRef = useRef(false);

  draftsRef.current = drafts;

  useEffect(() => {
    autoSubmittedRef.current = false;
  }, [attemptId]);

  const hydrateFromAttempt = useCallback((data: AttemptView) => {
    setAttempt(data);
    setRemainingSeconds(data.remaining_seconds);
    const initialDrafts: Record<string, Record<string, unknown>> = {};
    const initialSeqs: Record<string, number> = {};
    for (const q of data.questions) {
      const saved = data.responses[q.id];
      if (saved) {
        initialDrafts[q.id] = saved.payload;
        initialSeqs[q.id] = saved.client_seq;
      } else if (q.question_type === "coding") {
        const langs = Array.isArray(q.prompt.languages) ? (q.prompt.languages as string[]) : [];
        initialDrafts[q.id] = { language: langs[0] ?? "python3", source_code: "" };
      }
    }
    setDrafts(initialDrafts);
    seqRef.current = initialSeqs;
  }, []);

  useEffect(() => {
    if (navState?.initialAttempt) {
      hydrateFromAttempt(navState.initialAttempt);
      return;
    }
    if (!attemptId) return;
    let active = true;
    setLoading(true);
    getAttempt(attemptId)
      .then((data) => {
        if (active) hydrateFromAttempt(data);
      })
      .catch((err: unknown) => {
        if (active) setLoadError(err instanceof Error ? err.message : "Could not load attempt");
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, [attemptId, hydrateFromAttempt, navState?.initialAttempt]);

  // Server-synced 1s countdown
  useEffect(() => {
    if (!attempt || attempt.status !== "in_progress" || submission) return;
    const id = window.setInterval(() => {
      setRemainingSeconds((prev) => Math.max(0, prev - 1));
    }, 1000);
    return () => window.clearInterval(id);
  }, [attempt, submission]);

  // Fetch existing submission on finalized attempt reload
  useEffect(() => {
    if (!attemptId || !attempt || attempt.status === "in_progress" || submission) return;
    let active = true;
    getAttemptSubmission(attemptId)
      .then((res) => {
        if (active) setSubmission(res);
      })
      .catch(() => {});
    return () => {
      active = false;
    };
  }, [attemptId, attempt, submission]);

  // Poll submission status while async coding execution is evaluating/queued
  useEffect(() => {
    if (!attemptId || !submission) return;
    if (submission.status !== "evaluating" && submission.status !== "queued") return;
    let active = true;
    let polls = 0;
    const timer = window.setInterval(() => {
      polls += 1;
      if (polls > 40) {
        window.clearInterval(timer);
        return;
      }
      getAttemptSubmission(attemptId)
        .then((res) => {
          if (active) setSubmission(res);
        })
        .catch(() => {});
    }, 1500);
    return () => {
      active = false;
      window.clearInterval(timer);
    };
  }, [attemptId, submission]);

  // Clear pending debounce timers on unmount
  useEffect(() => {
    const timers = debounceRef.current;
    return () => {
      Object.values(timers).forEach((t) => window.clearTimeout(t));
    };
  }, []);

  const persistResponse = useCallback(
    async (questionId: string, payload: Record<string, unknown>) => {
      if (!attemptId) return;
      pendingDirtyRef.current.delete(questionId);
      const seq = nextClientSeq(seqRef.current, questionId);
      seqRef.current = { ...seqRef.current, [questionId]: seq };
      setSaveState("saving");
      setSaveError(null);
      try {
        const res = await saveAttemptResponse(attemptId, questionId, payload, seq);
        setLastSeq(res.client_seq);
        setSaveState("saved");
      } catch (err: unknown) {
        setSaveState("error");
        setSaveError(err instanceof Error ? err.message : "Autosave failed");
      }
    },
    [attemptId]
  );

  function scheduleSave(questionId: string, payload: Record<string, unknown>, delayMs: number) {
    pendingDirtyRef.current.add(questionId);
    const existing = debounceRef.current[questionId];
    if (existing) window.clearTimeout(existing);
    debounceRef.current[questionId] = window.setTimeout(() => {
      void persistResponse(questionId, payload);
    }, delayMs);
  }

  function updateDraft(
    q: CandidateQuestion,
    payload: Record<string, unknown>,
    debounceMs: number | null
  ) {
    setDrafts((prev) => ({ ...prev, [q.id]: payload }));
    if (debounceMs === null) {
      const existing = debounceRef.current[q.id];
      if (existing) window.clearTimeout(existing);
      void persistResponse(q.id, payload);
    } else {
      scheduleSave(q.id, payload, debounceMs);
    }
  }

  async function handleFileChange(q: CandidateQuestion, e: ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    e.target.value = "";
    if (!file || !attemptId) return;
    setUploading(true);
    setSaveState("saving");
    setSaveError(null);
    try {
      const uploaded = await uploadAttemptFile(attemptId, q.id, file);
      setDrafts((prev) => ({
        ...prev,
        [q.id]: {
          file_id: uploaded.file_id,
          original_name: uploaded.original_name,
          size_bytes: uploaded.size_bytes,
          sha256: uploaded.sha256,
        },
      }));
      setSaveState("saved");
    } catch (err: unknown) {
      setSaveState("error");
      setSaveError(err instanceof Error ? err.message : "Upload failed");
    } finally {
      setUploading(false);
    }
  }

  const handleSubmitExam = useCallback(
    async (options?: { auto?: boolean }) => {
      if (!attemptId || submittingRef.current) return;
      submittingRef.current = true;
      setSubmitting(true);
      if (options?.auto) {
        setAutoSubmitting(true);
      }
      setSaveError(null);

      // Flush any pending debounced text/code saves right before submitting.
      Object.values(debounceRef.current).forEach((t) => window.clearTimeout(t));
      const dirtyIds = Array.from(pendingDirtyRef.current);
      if (dirtyIds.length > 0) {
        await Promise.allSettled(
          dirtyIds.map((qid) => {
            const payload = draftsRef.current[qid];
            return payload ? persistResponse(qid, payload) : Promise.resolve();
          })
        );
      }

      try {
        const key = getOrCreateSubmitKey(attemptId);
        const res = await submitAttempt(attemptId, key);
        clearSubmitKey(attemptId);
        setSubmission(res);
        setConfirmSubmit(false);
      } catch (err: unknown) {
        if (err instanceof ApiError && err.code === "ALREADY_SUBMITTED") {
          clearSubmitKey(attemptId);
          try {
            const existing = await getAttemptSubmission(attemptId);
            setSubmission(existing);
            setConfirmSubmit(false);
            return;
          } catch {
            // Fall through to error display if status fetch also failed.
          }
        }
        setSaveError(err instanceof Error ? err.message : "Submission failed — please retry");
      } finally {
        submittingRef.current = false;
        setSubmitting(false);
        setAutoSubmitting(false);
      }
    },
    [attemptId, persistResponse]
  );

  // Auto-submit once when the countdown hits 00:00
  useEffect(() => {
    if (!attempt || attempt.status !== "in_progress" || submission) return;
    if (remainingSeconds <= 0 && !autoSubmittedRef.current) {
      autoSubmittedRef.current = true;
      setConfirmSubmit(false);
      void handleSubmitExam({ auto: true });
    }
  }, [attempt, remainingSeconds, submission, handleSubmitExam]);

  async function handleRunCode(q: CandidateQuestion) {
    if (!attemptId) return;
    const langs = Array.isArray(q.prompt.languages) ? (q.prompt.languages as string[]) : ["python3"];
    const language = String(drafts[q.id]?.language ?? langs[0]);
    const sourceCode = String(drafts[q.id]?.source_code ?? "");
    if (!sourceCode.trim()) {
      setRunErrors((prev) => ({ ...prev, [q.id]: "Write some code before running." }));
      return;
    }

    setRunningCode(true);
    setRunErrors((prev) => ({ ...prev, [q.id]: null }));
    const timer = debounceRef.current[q.id];
    if (timer) window.clearTimeout(timer);
    void persistResponse(q.id, { language, source_code: sourceCode });

    try {
      const res = await runAttemptCode(attemptId, q.id, {
        language,
        source_code: sourceCode,
        custom_stdin: useCustomStdin[q.id] ? (customStdin[q.id] ?? "") : null,
      });
      setRunResults((prev) => ({ ...prev, [q.id]: res }));
    } catch (err: unknown) {
      setRunErrors((prev) => ({
        ...prev,
        [q.id]: err instanceof Error ? err.message : "Code execution failed",
      }));
    } finally {
      setRunningCode(false);
    }
  }

  if (loading) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-canvas text-sm text-ink-muted">
        Loading assessment...
      </div>
    );
  }

  if (loadError || !attempt) {
    return (
      <div className="flex min-h-screen flex-col items-center justify-center gap-4 bg-canvas p-6 text-center">
        <p className="text-base font-bold text-danger">{loadError ?? "Attempt not found"}</p>
        <Link
          to="/candidate"
          className="rounded-full bg-accent px-6 py-2.5 text-sm font-bold text-on-accent"
        >
          Back to My Assessments
        </Link>
      </div>
    );
  }

  if (submission || attempt.status !== "in_progress") {
    return (
      <div className="flex min-h-screen items-center justify-center bg-canvas p-6">
        <div className="w-full max-w-lg rounded-2xl border border-subtle border-t-4 border-t-accent bg-surface p-8 text-center shadow-lg">
          <div className="mx-auto mb-4 inline-flex h-12 w-12 items-center justify-center rounded-full bg-accent-soft text-accent-text">
            <CheckCircle2 className="h-6 w-6" />
          </div>
          <p className="mb-1 text-xs font-bold uppercase tracking-wider text-accent-text">
            Attempt Finalized
          </p>
          <h1 className="mb-2 text-2xl font-extrabold text-ink">{title}</h1>
          <p className="mb-6 text-sm text-ink-secondary">
            Your responses have been recorded by the server.
          </p>

          {submission && (
            <div className="mb-6 space-y-2 rounded-xl border border-subtle bg-elevated p-4 text-sm">
              <div className="flex items-center justify-between">
                <span className="text-ink-secondary">Evaluation Status</span>
                <StatusBadge status={submission.status} />
              </div>
              <div className="flex items-center justify-between">
                <span className="text-ink-secondary">Current Score</span>
                <span className="font-extrabold text-ink">
                  {submission.score !== null ? submission.score : "Pending"}
                </span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-ink-secondary">Submission ID</span>
                <span className="font-mono text-xs text-ink-muted">
                  {submission.id.slice(0, 12)}…
                </span>
              </div>
            </div>
          )}

          <Link
            to="/candidate"
            className="inline-flex items-center justify-center rounded-full bg-accent px-6 py-3 text-sm font-bold text-on-accent hover:bg-accent-hover"
          >
            Return to My Assessments
          </Link>
        </div>
      </div>
    );
  }

  const questions = attempt.questions;
  const current = questions[currentIdx];
  const answeredCount = questions.filter((q) => {
    const d = drafts[q.id];
    if (!d) return false;
    if (q.question_type === "coding") return Boolean(String(d.source_code ?? "").trim());
    if (q.question_type === "descriptive") return Boolean(String(d.text ?? "").trim());
    if (q.question_type === "multiple_select")
      return Array.isArray(d.selected) && d.selected.length > 0;
    return true;
  }).length;

  const lowTime = remainingSeconds <= 300;

  return (
    <div className="min-h-screen flex flex-col bg-canvas text-ink">
      {/* Top Distraction-Free Exam Header */}
      <header className="sticky top-0 z-30 border-b border-subtle bg-surface/95 backdrop-blur-sm">
        <div className="mx-auto flex h-16 max-w-7xl items-center justify-between gap-4 px-4 sm:px-6">
          <div className="flex items-center gap-3">
            <span className="text-xl font-extrabold tracking-tight text-ink">
              LANCAST<span className="text-accent">.</span>
            </span>
            <span className="hidden h-5 w-px bg-subtle sm:inline-block" />
            <span className="hidden text-sm font-bold text-ink sm:inline-block">{title}</span>
          </div>

          <div
            className={`inline-flex items-center gap-2 rounded-full border px-4 py-1.5 text-sm font-extrabold tabular-nums ${
              lowTime
                ? "border-warn/40 bg-warn-soft text-warn"
                : "border-subtle bg-elevated text-ink"
            }`}
          >
            <Clock className="h-4 w-4" />
            {formatClock(remainingSeconds)}
          </div>

          <div className="flex items-center gap-2.5">
            <span className="hidden rounded-full border border-subtle bg-elevated px-3 py-1 text-xs font-semibold sm:inline-flex items-center gap-1.5">
              {saveState === "saving" && <span className="text-ink-muted">Saving…</span>}
              {saveState === "saved" && (
                <span className="text-accent-text">
                  Autosaved {lastSeq ? `• seq #${lastSeq}` : ""}
                </span>
              )}
              {saveState === "error" && <span className="text-danger">Save failed</span>}
              {saveState === "idle" && <span className="text-ink-muted">Ready</span>}
            </span>

            <button
              type="button"
              onClick={toggleTheme}
              aria-label="Toggle theme"
              className="cursor-pointer rounded-full border border-subtle bg-elevated p-2 text-ink"
            >
              {theme === "light" ? <Moon className="h-4 w-4" /> : <Sun className="h-4 w-4" />}
            </button>

            <button
              type="button"
              onClick={() => setConfirmSubmit(true)}
              className="inline-flex cursor-pointer items-center gap-1.5 rounded-full bg-accent px-5 py-2 text-xs font-bold text-on-accent shadow-sm hover:bg-accent-hover"
            >
              <Send className="h-3.5 w-3.5" /> Submit
            </button>
          </div>
        </div>
      </header>

      {/* Main Two-Column Runner */}
      <div className="mx-auto grid w-full max-w-7xl flex-1 gap-6 px-4 py-6 sm:px-6 lg:grid-cols-12">
        {/* Left Question Navigator */}
        <aside className="lg:col-span-3">
          <div className="flex flex-col justify-between gap-6 rounded-2xl border border-subtle bg-surface p-5 shadow-xs">
            <div>
              <h2 className="text-sm font-extrabold text-ink">Question Navigator</h2>
              <p className="mb-4 text-xs text-ink-muted">
                {answeredCount} of {questions.length} answered
              </p>

              <div className="grid grid-cols-5 gap-2 sm:grid-cols-6 lg:grid-cols-4">
                {questions.map((q, idx) => {
                  const isCurrent = idx === currentIdx;
                  const d = drafts[q.id];
                  const isAnswered =
                    Boolean(d) &&
                    (q.question_type === "coding"
                      ? Boolean(String(d.source_code ?? "").trim())
                      : q.question_type === "descriptive"
                        ? Boolean(String(d.text ?? "").trim())
                        : q.question_type === "multiple_select"
                          ? Array.isArray(d.selected) && d.selected.length > 0
                          : true);

                  return (
                    <button
                      key={q.id}
                      type="button"
                      onClick={() => setCurrentIdx(idx)}
                      className={`h-10 cursor-pointer rounded-xl border text-xs font-extrabold transition ${
                        isCurrent
                          ? "border-accent bg-accent text-on-accent shadow-xs"
                          : isAnswered
                            ? "border-accent-border bg-accent-soft text-accent-text"
                            : "border-subtle bg-elevated/60 text-ink-secondary hover:border-strong"
                      }`}
                    >
                      {q.position}
                    </button>
                  );
                })}
              </div>
            </div>

            <div className="rounded-xl border border-subtle bg-elevated/60 p-3.5 text-xs leading-relaxed text-ink-muted">
              <strong className="block text-ink">Server-Authoritative Deadline</strong>
              Saves are verified with monotonic sequence numbers to protect against network
              glitches.
            </div>
          </div>
        </aside>

        {/* Right Active Question */}
        <main className="lg:col-span-9">
          {autoSubmitting && (
            <div className="mb-4 flex items-center gap-2 rounded-xl border border-warn/30 bg-warn-soft px-4 py-3 text-xs font-semibold text-warn">
              <Clock className="h-4 w-4 shrink-0" />
              Time expired — automatically submitting your responses...
            </div>
          )}

          {saveError && (
            <div className="mb-4 flex items-center gap-2 rounded-xl bg-danger-soft px-4 py-3 text-xs font-semibold text-danger">
              <AlertTriangle className="h-4 w-4 shrink-0" />
              {saveError}
            </div>
          )}

          {current && (
            <div className="flex flex-col justify-between rounded-2xl border border-subtle bg-surface p-6 shadow-xs sm:p-8">
              <div className="space-y-5">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <span className="text-xs font-bold uppercase tracking-wider text-accent-text">
                    Question {current.position} of {questions.length} •{" "}
                    {current.question_type.replace("_", " ")}
                  </span>
                  <span className="rounded-full border border-accent-border bg-accent-soft px-3 py-0.5 text-xs font-bold text-accent-text">
                    {current.max_score} Points
                  </span>
                </div>

                <h2 className="text-xl font-extrabold leading-snug text-ink">
                  {String(current.prompt.text ?? "")}
                </h2>

                {/* MCQ */}
                {current.question_type === "mcq" && (
                  <div className="space-y-2.5">
                    {(current.prompt.options as { id: string; text: string }[]).map((opt) => {
                      const selected = drafts[current.id]?.selected === opt.id;
                      return (
                        <button
                          key={opt.id}
                          type="button"
                          onClick={() => updateDraft(current, { selected: opt.id }, null)}
                          className={`flex w-full cursor-pointer items-center gap-3 rounded-xl border px-4 py-3.5 text-left text-sm transition ${
                            selected
                              ? "border-accent bg-accent-soft font-bold text-ink"
                              : "border-subtle bg-elevated/40 text-ink-secondary hover:border-strong hover:text-ink"
                          }`}
                        >
                          <span
                            className={`flex h-5 w-5 shrink-0 items-center justify-center rounded-full border text-[11px] font-bold ${
                              selected
                                ? "border-accent bg-accent text-on-accent"
                                : "border-strong bg-surface"
                            }`}
                          >
                            {opt.id}
                          </span>
                          <span>{opt.text}</span>
                        </button>
                      );
                    })}
                  </div>
                )}

                {/* Multiple Select */}
                {current.question_type === "multiple_select" && (
                  <div className="space-y-2.5">
                    {(current.prompt.options as { id: string; text: string }[]).map((opt) => {
                      const currentSelected = Array.isArray(drafts[current.id]?.selected)
                        ? (drafts[current.id].selected as string[])
                        : [];
                      const checked = currentSelected.includes(opt.id);
                      return (
                        <button
                          key={opt.id}
                          type="button"
                          onClick={() => {
                            const next = checked
                              ? currentSelected.filter((x) => x !== opt.id)
                              : [...currentSelected, opt.id];
                            updateDraft(current, { selected: next }, null);
                          }}
                          className={`flex w-full cursor-pointer items-center gap-3 rounded-xl border px-4 py-3.5 text-left text-sm transition ${
                            checked
                              ? "border-accent bg-accent-soft font-bold text-ink"
                              : "border-subtle bg-elevated/40 text-ink-secondary hover:border-strong hover:text-ink"
                          }`}
                        >
                          <input
                            type="checkbox"
                            readOnly
                            checked={checked}
                            className="h-4 w-4 accent-emerald-600"
                          />
                          <span>{opt.text}</span>
                        </button>
                      );
                    })}
                  </div>
                )}

                {/* Descriptive */}
                {current.question_type === "descriptive" && (() => {
                  const maxLen = Number(current.prompt.max_length ?? 5000);
                  const val = String(drafts[current.id]?.text ?? "");
                  return (
                    <div className="space-y-2">
                      <textarea
                        rows={8}
                        maxLength={maxLen}
                        value={val}
                        onChange={(e) => updateDraft(current, { text: e.target.value }, 600)}
                        placeholder="Write your answer here..."
                        className="w-full rounded-xl border border-strong bg-input p-4 text-sm leading-relaxed text-ink focus:border-accent focus:outline-none focus:ring-2 focus:ring-accent/20"
                      />
                      <div className="flex items-center justify-between text-xs text-ink-muted">
                        <span>
                          {val.length} / {maxLen} characters
                        </span>
                        <button
                          type="button"
                          onClick={() => void persistResponse(current.id, { text: val })}
                          className="cursor-pointer font-bold text-accent-text hover:underline"
                        >
                          Save Now
                        </button>
                      </div>
                    </div>
                  );
                })()}

                {/* File Upload */}
                {current.question_type === "file_upload" && (() => {
                  const exts = Array.isArray(current.prompt.allowed_extensions)
                    ? (current.prompt.allowed_extensions as string[])
                    : [];
                  const maxBytes = Number(current.prompt.max_size_bytes ?? 1048576);
                  const uploaded = drafts[current.id];
                  return (
                    <div className="space-y-4 rounded-xl border border-subtle bg-elevated/50 p-5">
                      <div className="text-xs text-ink-secondary">
                        Allowed formats:{" "}
                        <span className="font-bold text-ink">
                          {exts.map((e) => `.${e}`).join(", ")}
                        </span>{" "}
                        • Max size:{" "}
                        <span className="font-bold text-ink">
                          {Math.round((maxBytes / (1024 * 1024)) * 10) / 10} MB
                        </span>
                      </div>

                      <label className="inline-flex cursor-pointer items-center gap-2 rounded-full bg-accent px-5 py-2.5 text-xs font-bold text-on-accent hover:bg-accent-hover">
                        <Upload className="h-4 w-4" />
                        {uploading ? "Uploading..." : "Choose File to Upload"}
                        <input
                          type="file"
                          disabled={uploading}
                          accept={exts.map((e) => `.${e}`).join(",")}
                          onChange={(e) => void handleFileChange(current, e)}
                          className="hidden"
                        />
                      </label>

                      {uploaded && Boolean(uploaded.file_id) && (
                        <div className="rounded-xl border border-accent-border bg-accent-soft p-3.5 text-xs text-accent-text">
                          <div className="font-bold">
                            Uploaded: {String(uploaded.original_name)} (
                            {Number(uploaded.size_bytes)} bytes)
                          </div>
                          <div className="mt-1 font-mono opacity-85">
                            SHA-256: {String(uploaded.sha256)}
                          </div>
                        </div>
                      )}
                    </div>
                  );
                })()}

                {/* Coding */}
                {current.question_type === "coding" && (() => {
                  const langs = Array.isArray(current.prompt.languages)
                    ? (current.prompt.languages as string[])
                    : ["python3"];
                  const samples = Array.isArray(current.prompt.sample_cases)
                    ? (current.prompt.sample_cases as {
                        stdin: string;
                        expected_stdout: string;
                      }[])
                    : [];
                  const curLang = String(drafts[current.id]?.language ?? langs[0]);
                  const code = String(drafts[current.id]?.source_code ?? "");

                  return (
                    <div className="space-y-4">
                      {samples.length > 0 && (
                        <div className="grid gap-3 sm:grid-cols-2">
                          {samples.map((s, idx) => (
                            <div
                              key={idx}
                              className="rounded-xl border border-subtle bg-elevated/60 p-3 text-xs"
                            >
                              <div className="mb-1 font-bold uppercase tracking-wider text-ink-muted">
                                Sample #{idx + 1}
                              </div>
                              <pre className="font-mono text-ink">
                                Input: {s.stdin || "(empty)"}
                                {"\n"}Output: {s.expected_stdout}
                              </pre>
                            </div>
                          ))}
                        </div>
                      )}

                      <div className="overflow-hidden rounded-xl border border-strong">
                        <div className="flex flex-wrap items-center justify-between gap-2 border-b border-subtle bg-elevated px-4 py-2.5">
                          <div className="flex items-center gap-3">
                            <select
                              aria-label="Programming language"
                              value={curLang}
                              onChange={(e) =>
                                updateDraft(
                                  current,
                                  { language: e.target.value, source_code: code },
                                  code.trim() ? 300 : null
                                )
                              }
                              className="rounded-full border border-strong bg-surface px-3 py-1 text-xs font-bold text-ink"
                            >
                              {langs.map((l) => (
                                <option key={l} value={l}>
                                  {LANGUAGE_LABELS[l] ?? l}
                                </option>
                              ))}
                            </select>

                            <label className="inline-flex cursor-pointer items-center gap-1.5 text-xs font-semibold text-ink-secondary">
                              <input
                                type="checkbox"
                                checked={Boolean(useCustomStdin[current.id])}
                                onChange={(e) =>
                                  setUseCustomStdin((prev) => ({
                                    ...prev,
                                    [current.id]: e.target.checked,
                                  }))
                                }
                                className="h-3.5 w-3.5 accent-emerald-600"
                              />
                              Custom Input
                            </label>
                          </div>

                          <div className="flex items-center gap-3">
                            <button
                              type="button"
                              onClick={() => {
                                if (code.trim()) {
                                  void persistResponse(current.id, {
                                    language: curLang,
                                    source_code: code,
                                  });
                                }
                              }}
                              className="cursor-pointer text-xs font-bold text-ink-secondary hover:text-ink hover:underline"
                            >
                              Save Code
                            </button>
                            <button
                              type="button"
                              disabled={runningCode}
                              onClick={() => void handleRunCode(current)}
                              className="inline-flex cursor-pointer items-center gap-1.5 rounded-full bg-accent px-4 py-1.5 text-xs font-bold text-on-accent shadow-xs hover:bg-accent-hover disabled:opacity-60"
                            >
                              <Play className="h-3 w-3" />
                              {runningCode ? "Running..." : "Run Code"}
                            </button>
                          </div>
                        </div>

                        <CodeEditor
                          value={code}
                          language={curLang}
                          theme={theme}
                          placeholder={`Write your ${curLang} solution here...`}
                          onChange={(nextCode) =>
                            updateDraft(
                              current,
                              { language: curLang, source_code: nextCode },
                              800
                            )
                          }
                        />
                      </div>

                      {useCustomStdin[current.id] && (
                        <div className="rounded-xl border border-subtle bg-elevated/50 p-3.5">
                          <label className="mb-1.5 block text-xs font-bold uppercase tracking-wider text-ink-muted">
                            Custom Standard Input (stdin)
                          </label>
                          <textarea
                            rows={3}
                            value={customStdin[current.id] ?? ""}
                            onChange={(e) =>
                              setCustomStdin((prev) => ({
                                ...prev,
                                [current.id]: e.target.value,
                              }))
                            }
                            placeholder="Enter custom input to test your code..."
                            className="w-full rounded-lg border border-strong bg-input p-2.5 font-mono text-xs text-ink"
                          />
                        </div>
                      )}

                      {runErrors[current.id] && (
                        <div className="rounded-xl bg-danger-soft px-4 py-3 text-xs font-semibold text-danger">
                          {runErrors[current.id]}
                        </div>
                      )}

                      {runResults[current.id] && (
                        <div className="space-y-3 rounded-xl border border-subtle bg-elevated/50 p-4">
                          <div className="flex items-center justify-between">
                            <span className="text-xs font-extrabold uppercase tracking-wider text-ink">
                              Run Output
                            </span>
                            <span className="rounded-full border border-subtle bg-surface px-3 py-0.5 text-[11px] font-bold text-ink-secondary">
                              {runResults[current.id].mode === "sample_cases"
                                ? "Public Sample Cases"
                                : "Custom Input"}
                            </span>
                          </div>

                          {runResults[current.id].cases.map((c, idx) => (
                            <div
                              key={idx}
                              className="space-y-2 rounded-xl border border-subtle bg-surface p-3.5 text-xs"
                            >
                              <div className="flex items-center justify-between">
                                <span className="font-bold text-ink">Case #{idx + 1}</span>
                                <div className="flex items-center gap-2">
                                  {c.time_sec !== null && (
                                    <span className="font-mono text-ink-muted">
                                      {c.time_sec}s
                                    </span>
                                  )}
                                  <span
                                    className={`rounded-full border px-2.5 py-0.5 text-[11px] font-bold uppercase ${
                                      c.passed === true
                                        ? "border-accent-border bg-accent-soft text-accent-text"
                                        : c.passed === false ||
                                            c.verdict === "compile_error" ||
                                            c.verdict === "runtime_error" ||
                                            c.verdict === "timed_out"
                                          ? "border-danger/30 bg-danger-soft text-danger"
                                          : "border-subtle bg-elevated text-ink-secondary"
                                    }`}
                                  >
                                    {c.verdict.replace("_", " ")}
                                  </span>
                                </div>
                              </div>

                              <div className="grid gap-2 sm:grid-cols-2">
                                <div>
                                  <div className="mb-0.5 font-bold text-ink-muted">Input</div>
                                  <pre className="overflow-x-auto rounded-lg bg-elevated p-2 font-mono text-ink">
                                    {c.stdin || "(empty)"}
                                  </pre>
                                </div>
                                {c.expected_stdout !== null && (
                                  <div>
                                    <div className="mb-0.5 font-bold text-ink-muted">Expected</div>
                                    <pre className="overflow-x-auto rounded-lg bg-elevated p-2 font-mono text-ink">
                                      {c.expected_stdout || "(empty)"}
                                    </pre>
                                  </div>
                                )}
                              </div>

                              <div>
                                <div className="mb-0.5 font-bold text-ink-muted">Your Output</div>
                                <pre className="overflow-x-auto rounded-lg bg-elevated p-2 font-mono text-ink">
                                  {c.stdout || "(empty)"}
                                </pre>
                              </div>

                              {(c.stderr || c.compile_output) && (
                                <div>
                                  <div className="mb-0.5 font-bold text-danger">
                                    Errors / Compiler Output
                                  </div>
                                  <pre className="overflow-x-auto rounded-lg bg-danger-soft p-2 font-mono text-danger">
                                    {c.compile_output || c.stderr}
                                  </pre>
                                </div>
                              )}
                            </div>
                          ))}
                        </div>
                      )}
                    </div>
                  );
                })()}
              </div>

              {/* Navigation Footer */}
              <div className="mt-8 flex items-center justify-between border-t border-subtle pt-5">
                <button
                  type="button"
                  disabled={currentIdx === 0}
                  onClick={() => setCurrentIdx((i) => Math.max(0, i - 1))}
                  className="inline-flex cursor-pointer items-center gap-1.5 rounded-full border border-strong bg-surface px-5 py-2 text-xs font-bold text-ink disabled:cursor-not-allowed disabled:opacity-40"
                >
                  <ArrowLeft className="h-3.5 w-3.5" /> Previous
                </button>

                {currentIdx < questions.length - 1 ? (
                  <button
                    type="button"
                    onClick={() => setCurrentIdx((i) => Math.min(questions.length - 1, i + 1))}
                    className="inline-flex cursor-pointer items-center gap-1.5 rounded-full bg-accent px-6 py-2 text-xs font-bold text-on-accent hover:bg-accent-hover"
                  >
                    Next Question <ArrowRight className="h-3.5 w-3.5" />
                  </button>
                ) : (
                  <button
                    type="button"
                    onClick={() => setConfirmSubmit(true)}
                    className="inline-flex cursor-pointer items-center gap-1.5 rounded-full bg-accent px-6 py-2 text-xs font-bold text-on-accent hover:bg-accent-hover"
                  >
                    Review &amp; Submit <Send className="h-3.5 w-3.5" />
                  </button>
                )}
              </div>
            </div>
          )}
        </main>
      </div>

      {/* Confirm Submit Modal */}
      {confirmSubmit && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4 backdrop-blur-xs">
          <div className="w-full max-w-md rounded-2xl border border-subtle bg-surface p-6 shadow-2xl">
            <h2 className="mb-2 text-lg font-extrabold text-ink">Submit Assessment?</h2>
            <p className="mb-4 text-sm text-ink-secondary">
              You have answered <strong>{answeredCount}</strong> of{" "}
              <strong>{questions.length}</strong> questions. Once submitted, no further changes can
              be made.
            </p>
            <div className="flex justify-end gap-2.5">
              <button
                type="button"
                onClick={() => setConfirmSubmit(false)}
                className="cursor-pointer rounded-full border border-strong bg-surface px-5 py-2 text-sm font-semibold text-ink"
              >
                Keep Working
              </button>
              <button
                type="button"
                disabled={submitting}
                onClick={() => void handleSubmitExam()}
                className="cursor-pointer rounded-full bg-accent px-6 py-2 text-sm font-bold text-on-accent hover:bg-accent-hover disabled:opacity-60"
              >
                {submitting ? "Submitting..." : "Confirm Submit"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
